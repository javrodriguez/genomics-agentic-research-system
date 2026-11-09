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
    # FURNITURE FILLED 21 Oct 2026 (lane d8-furniture, glitch-f1 under Javier's delegation): the per-harness
    # positions read from the walks (TestFurniture); nothing is PENDING in this module now.
    def test_the_pending_set(self):
        self.assertEqual(sr.pending(), {})
        self.assertNotEqual(sr.FURNITURE, "PENDING")
        self.assertNotEqual(sr.RULES_SCANNER, "PENDING")

    def test_each_refuses_a_real_use(self):
        with mock.patch.object(sr, "RULES_SCANNER", sr.PENDING):
            with self.assertRaises(sr.NotReady):
                sr.real_rules_scanner()
            self.assertEqual(set(sr.pending()), {"rules_scanner"})
        with mock.patch.object(sr, "FURNITURE", sr.PENDING):
            with self.assertRaises(sr.NotReady):
                sr.furniture_positions("a-harness")
            self.assertEqual(set(sr.pending()), {"furniture"})
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


# ------------------------------------------------------------------------------------------------- FURNITURE
# Lane d8-furniture (21 Oct 2026): the per-harness positions of what each CLI writes itself into its stream or session
# file, read from the walks (D8-READ-w-o46-20261021.md, D8-READ-w-g21-20261021.md; the lane's survey of all 225 walks).
# The binding of each entry's evidence to the walk line it names is test_awareness_furniture's (it holds the
# record-kind rule); here, the shape and the account positions.
HARNESS_NAMES = {"claude-code", "codex", "gemini"}
CODEX_IDENTIFYING = {("session", "session_meta", "payload.creator_user_id"),
                     ("session", "session_meta", "payload.creator_account_id")}
CODEX_PLAN = {("session", "event_msg/token_count", f)
              for f in ("payload.rate_limits.plan_type", "payload.rate_limits.credits.has_credits",
                        "payload.rate_limits.credits.unlimited", "payload.rate_limits.credits.balance")}
_EVIDENCE = re.compile(r"(w\d+|w-[og]\d+)/[A-Za-z0-9._/-]+\.jsonl:[1-9]\d*|transcript_view\.py:[1-9]\d*")


def furniture_shape_problems(furniture) -> list:
    out = []
    if not isinstance(furniture, dict) or set(furniture) != HARNESS_NAMES:
        return [f"FURNITURE is not keyed by exactly {sorted(HARNESS_NAMES)}"]
    for h, entries in furniture.items():
        if not isinstance(entries, tuple) or not entries:
            out.append(f"{h}: not a non-empty tuple")
            continue
        seen = set()
        for i, e in enumerate(entries):
            where = f"{h}[{i}]"
            if not isinstance(e, dict) or set(e) != set(sr.FURNITURE_KEYS):
                out.append(f"{where}: keys are not exactly {sr.FURNITURE_KEYS}")
                continue
            if e["file"] not in ("session", "stream"):
                out.append(f"{where}: file {e['file']!r}")
            if not isinstance(e["record"], str) or not e["record"]:
                out.append(f"{where}: record")
            if not isinstance(e["fields"], tuple) or not e["fields"] or \
                    not all(isinstance(f, str) and f for f in e["fields"]):
                out.append(f"{where}: fields")
            if e["account"] not in sr.ACCOUNT_CLASSES:
                out.append(f"{where}: account {e['account']!r}")
            if e["account"] and "*" in e["fields"]:
                out.append(f"{where}: an account entry names its fields, never the whole record")
            if not isinstance(e["evidence"], tuple) or not e["evidence"] or \
                    not all(isinstance(x, str) and _EVIDENCE.fullmatch(x) for x in e["evidence"]):
                out.append(f"{where}: evidence is not walk folder/file:line strings")
            if h != "claude-code" and any(x.startswith("transcript_view.py:") for x in e["evidence"]):
                out.append(f"{where}: a vendor entry cites no walk")
            key = (e["file"], e["record"], e["account"])
            if key in seen:
                out.append(f"{where}: a second entry for {key}")
            seen.add(key)
    return out


class TestFurniture(unittest.TestCase):
    def test_the_shape(self):
        self.assertEqual(furniture_shape_problems(sr.FURNITURE), [])

    def test_codex_account_positions(self):
        got = {(e["file"], e["record"], f, e["account"]) for e in sr.account_positions("codex") for f in e["fields"]}
        self.assertEqual(got, {k + ("identifying",) for k in CODEX_IDENTIFYING} | {k + ("plan",) for k in CODEX_PLAN})

    def test_gemini_has_no_account_field_and_claude_none_identifying(self):
        # Gemini's one candidate, projectHash, is sha256 of the run-tree path (36 of 36 walks, the lane's survey).
        self.assertEqual(sr.account_positions("gemini"), ())
        self.assertFalse([e for e in sr.account_positions("claude-code") if e["account"] == "identifying"])
        self.assertTrue(sr.account_positions("claude-code"))

    def test_the_account_positions_are_furniture_positions(self):
        for h in HARNESS_NAMES:
            self.assertTrue(set(map(id, sr.account_positions(h))) <= set(map(id, sr.furniture_positions(h))))

    def test_the_codex_developer_entry_cites_a_pre_and_a_post_b22_walk(self):
        (dev,) = [e for e in sr.FURNITURE["codex"] if e["record"] == "response_item/message/developer"]
        self.assertTrue(any(x.startswith("w-o46/") for x in dev["evidence"]))
        self.assertTrue(any(x.startswith("w-o47/") for x in dev["evidence"]))

    def test_mutants_go_red(self):
        extra = {"file": "session", "record": "x", "fields": ("*",), "account": "identifying",
                 "evidence": ("w-o46/a.jsonl:1",)}
        self.assertTrue(furniture_shape_problems(dict(sr.FURNITURE, codex=sr.FURNITURE["codex"] + (extra,))))
        red("an account entry naming the whole record")
        self.assertTrue(furniture_shape_problems({h: v for h, v in sr.FURNITURE.items() if h != "gemini"}))
        red("a harness dropped from FURNITURE")
        bad = dict(sr.FURNITURE, gemini=tuple(dict(e, evidence=("operator words",)) for e in sr.FURNITURE["gemini"]))
        self.assertTrue(furniture_shape_problems(bad))
        red("evidence that is not a walk line")


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
        # lane vendor-b24 (B24-2 item 5 as revised): a shell read's absolute path resolves inside a run tree
        self.doc = "/tmp/run-c8021046/gars/_references/environment.md"
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

    # ---- od57-line (SCANREFUSAL-ROAD-20261108; Javier's word pending, ask od57-line): an older refusal witness the
    # widening admits is retargeted, never dropped. The record is admitted as is (a whole shell output line after a
    # closed prefix); with the fallback off (reads_only) its read rule refuses it exactly as before, its mutants
    # included; and its nearest shape, one byte after every copy of the pinned bytes (line_twin), still refuses.
    @staticmethod
    def reads_only():
        """box/od57_rule with od57-line's fallback off (_any_text admits nothing): the read rules alone."""
        from box import od57_rule
        return mock.patch.object(od57_rule, "_any_text", lambda *a, **k: None)

    def line_twin(self, body: bytes) -> bytes:
        """The record with one byte after every copy of the pinned bytes: od57-line's nearest refusal."""
        t = self.text.encode()
        self.assertIn(t, body)
        return body.replace(t, t + b"~")

    def od57_line(self, refuses, admits, body):
        """A retargeted witness: `admits(body)` as is, `refuses(body)` with the fallback off (the old witness), and
        `refuses(line_twin(body))` as is."""
        admits(body)
        with self.reads_only():
            refuses(body)
        refuses(self.line_twin(body))

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
                (f"grep -Hn pinned {self.doc}", f"{self.doc}:175:{self.text}\n",
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
            # od57-gap follow-up: `sed -n 175p <doc>` is now a ruled bare read of the doc; `sort <doc>` stays no read
            "a Bash that is not cat or grep": self.bash_record(f"sort {self.doc}", self.text + "\n"),
            "a Bash that only starts with grep's letters": self.bash_record(f"grepx {self.doc}", self.text + "\n"),
            "a result whose tool_use is missing": _cc(_result("toolu_X", f"175\t{self.text}")),
            "an Agent's result": _cc(_use("toolu_A", "Agent", {"prompt": "read it"}),
                                     _result("toolu_A", f"{self.text}\n")),
            "the line with more on it": self.bash_record(f"cat {self.doc}", f"{self.text} and more\n"),
        }
        # od57-line: a Bash result's whole line is admitted whatever the command (retargeted, see od57_line)
        line = ("a Bash that is not cat or grep", "a Bash that only starts with grep's letters")

        def refuses(body):
            p = self.write("transcript.jsonl", body)
            r, _ = self.scan([(p, "transcript")])
            self.assertEqual(r["ruled"], [])
            self.assertEqual([x["why"] for x in r["refused"]], [f"the rules scanner's rule {OD57_RULE!r}"])

        def admits(body):
            p = self.write("transcript.jsonl", body)
            r, _ = self.scan([(p, "transcript")])
            self.assertEqual((r["refused"], [x["line"] for x in r["ruled"]]), ([], [2]))
        for name, body in cases.items():
            with self.subTest(name):
                if name in line:
                    self.od57_line(refuses, admits, body)
                else:
                    refuses(body)

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
        from box import od57_rule
        with mock.patch.object(od57_rule, "_claude_tool", lambda uses, uid: od57_rule._ruled_shell("cat " + DOC_REL)):
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
    """sr.<fn_name> (or, since lane vendor-b24 moved OD57's rule there, box/od57_rule.<fn_name>) rebuilt from its source
    with each (old, new) edit applied once, as a mock patch on the module that defines it."""
    from box import od57_rule
    mod = sr if fn_name in vars(sr) and getattr(sr, fn_name).__module__ == sr.__name__ else od57_rule
    src = textwrap.dedent(inspect.getsource(getattr(mod, fn_name)))
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"mutant edit {old!r} matches {src.count(old)} times in {fn_name}")
        src = src.replace(old, new)
    ns = dict(vars(mod))
    exec(compile(src, f"{fn_name}_mutant", "exec"), ns)
    return mock.patch.object(mod, fn_name, ns[fn_name])


class TestOD57Chain(TestOD57Ruling):
    """Inherits TestOD57Ruling's fixtures; its own tests below (the parent's run once, in the parent)."""

    def grep_out(self, text=None):
        return f"_references/environment.md:175:{self.text if text is None else text}\n"

    def admitted(self, body, kind="transcript", scanner=None):
        p = self.write(f"{kind}.jsonl", body)
        r, _ = self.scan([(p, kind)], scanner)
        return r["ruled"] != [] and r["refused"] == []

    def line_retarget(self, body, kind="transcript"):
        """od57-line: an older refusal witness, retargeted (TestOD57Ruling.od57_line) on `admitted`."""
        self.od57_line(lambda b: self.assertFalse(self.admitted(b, kind)),
                       lambda b: self.assertTrue(self.admitted(b, kind)), body)

    def test_witness_w167s_command_is_admitted_in_its_transcript_and_its_stream(self):
        for kind, side in (("transcript", False), ("stream", True)):
            with self.subTest(kind=kind):
                self.assertTrue(self.admitted(self.bash_record(W167, self.grep_out(), side), kind))

    def test_the_bash_shapes(self):
        doc = "_references/environment.md"
        admitted = [W167, "grep -n pinned " + doc, "cat " + doc, "cat -n /tmp/run-c8021046/gars/" + doc,
                    "cd /tmp/run-c8021046/gars && grep -n Key " + doc + " | sort | uniq | wc -l",

                    "grep -n Key " + doc + " 2>&1 | head", "grep -n Key " + doc + " | tail -3",
                    "grep 'Key pinned' " + doc, 'grep -n "a\\|b" ' + doc]
        refused = ["cd x && sed -n 175p " + doc, "grep -n pinned _references/other.md", "echo $(cat " + doc + ")",
                   'cat "$(cat x)/' + doc + '"', 'cat "`cat x`/' + doc + '"', "eval cat " + doc,
                   "sh -c 'cat " + doc + "'", "bash -c 'grep -n Key " + doc + "'", "cat " + doc + " | sh -c 'cat y'",
                   'grep "unclosed ' + doc, "echo hi && grep -n Key " + doc, "cat <(" + doc + ")",
                   "grep -n Key " + doc + " &", "(cat " + doc + ")", "cd && grep -n Key " + doc,
                   # B24 R3-2 (review of 7fcba34, MINOR-2): a recursive grep's labels come from filenames on disk
                   "grep -rn Key /tmp/run-c8021046/gars/_references", "cat " + doc + "x", "cat " + doc + ".bak", "cat my" + doc,
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
                if name == "a user-text copy":          # no Bash result: od57-line never reads it
                    self.assertFalse(self.admitted(body))
                else:                                   # od57-line: a whole Bash output line, retargeted
                    self.line_retarget(body)

    def test_mutation_witnesses_of_the_bash_shapes(self):
        LINE = self.text
        # lane vendor-b24 moved the allow-list into box/od57_rule (_shell_tokens, _ruled_shell, _grep_spec,
        # _filter_ok); each witness is the same refusal, its guard named where it now lives
        cases = (
            ("the doc path dropped", "grep -n pinned _references/other.md", "175:%s\n" % LINE,
             "_grep_spec", ("if not _resolves_to_doc(ops[0], cwd):", "if False:")),
            # od57-gap follow-up: `head -200 <doc>` is now a ruled bare read (_ruled_compound); `nl` is still no read
            ("the grep-or-cat first word dropped", "cd gars && nl _references/environment.md", LINE + "\n",
             "_ruled_shell", ("    else:\n        return None\n    if spec is None:",
                              "    else:\n        spec = _cat_spec([a for a in read[1:] if a[:1] != '-'], cwd)\n"
                              "    if spec is None:")),
            ("the substitution guard dropped", 'grep "$(cat /tmp/p)" _references/environment.md', LINE + "\n",
             "_shell_tokens", ('"$(", "`", ', "")),
            ("the allow-list dropped", "grep -n Key _references/environment.md; xargs cat /tmp/other",
             "175:%s\n" % LINE, "_filter_ok", ("if form is None:\n        return False",
                                              "if form is None:\n        return True")),
            ("the newline refusal dropped", "grep -n Key\n_references/environment.md",
             "175:%s\n" % LINE, "_shell_tokens", (r'"\n", "\r", ', "")),
            ("the backslash refusal dropped", "\\grep -n Key _references/environment.md", "175:%s\n" % LINE,
             "_shell_tokens", ("if _ruled_unquoted_backslash(cmd):", "if False:")),
        )
        for name, cmd, out, fn, edit in cases:
            with self.subTest(name):
                body = self.bash_record(cmd, out)
                # od57-line admits each whole line as is, and refuses it with a byte after the pinned bytes; each
                # guard keeps its witness on the read rules alone (the fallback off)
                self.assertTrue(self.admitted(body))
                self.assertFalse(self.admitted(self.line_twin(body)))
                with self.reads_only():
                    self.assertFalse(self.admitted(body))
                    with _mutant(fn, edit):
                        self.assertTrue(self.admitted(body), f"{name}: the mutant still refuses")
                red(f"OD57 w167: {name}")

    def test_mutation_witnesses_of_the_hash_fixes(self):
        """The review of b2738e2: the # refusal and the empty commenters, each with its own witness."""
        # the # refusal: a # anywhere refuses, so a pattern holding one refuses; dropped, it admits
        benign = 'grep -n "#Key" _references/environment.md'
        self.assertFalse(sr._ruled_bash(benign))
        with _mutant("_shell_tokens", ('"#", ', '')):
            self.assertTrue(sr._ruled_bash(benign), "the # refusal dropped: still refused")
        red("OD57 #: the # refusal dropped")
        # the empty commenters: with the # refusal dropped, they alone still refuse the review's repros; with both
        # dropped, shlex's comment hides the shell and the repros admit
        for repro in ("grep -n Key _references/environment.md x#; sh -c 'cat /tmp/other'", "cat _references/environment.md#;python3 -c 'print(1)'"):
            with self.subTest(repro=repro):
                self.assertFalse(sr._ruled_bash(repro))
                with _mutant("_shell_tokens", ('"#", ', '')):
                    self.assertFalse(sr._ruled_bash(repro), "the empty commenters do not refuse it alone")
                with _mutant("_shell_tokens", ('"#", ', ''), ('lex.commenters = ""', 'pass')):
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
            with _mutant("ruled_text", (conjunct, "False")):
                self.assertTrue(self.admitted(body), f"the mutant still refuses: no witness of {conjunct!r}")
        red(f"OD57 nowhere-else: {conjunct}")

    def test_the_same_record_case_refuses_and_the_whole_guard_is_what_refuses_it(self):
        rec = _result("toolu_R", [{"type": "text", "text": f"175\t{self.text}\n"}])
        rec["message"]["content"].append({"type": "text", "text": f"please check this:\n{self.text}\n"})
        body = _cc(_use("toolu_R", "Read", {"file_path": self.doc}), rec)
        self.assertFalse(self.admitted(body))
        with _mutant("ruled_text", (NOT_ESCAPED, "False"), (DECODED_ELSEWHERE, "False"), (RAW_ELSEWHERE, "False")):
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


# ------------------------------------------------------------------------------------------------- OD57, the other arms
# Lane vendor-b17 round 1 (glitch-26's rulings B17-1 to B17-3; lane-reports/B17-DESIGN-NOTE.md): practice walk w-g9 was
# held at the drive scan on the ruled line inside the Gemini arm's read of the doc, in its turn stream and its native
# session file. The records below are synthesized in each shape the design note names for the Gemini and Codex arms:
# their keys from the pinned sources the note cites, every value invented here, never text from a real walk record; the
# ruled line is read at test time, as above. The shape tests (test_*_admitted) are RED on the round's head 67075247 by
# design: today scan_record admits the line only inside a Claude Code tool_result. The refusal tests must stay green
# after any fix.
TS = "2026-10-19T00:00:00.000Z"
DOC_REL = "_references/environment.md"
SHELL_READS = (("cat", "cat " + DOC_REL), ("grep-n", "grep -n pinned " + DOC_REL), ("grep", "grep pinned " + DOC_REL))


def _gem_use(cid, name, params):            # Gemini CLI stream-json tool_use
    return {"type": "tool_use", "timestamp": TS, "tool_name": name, "tool_id": cid, "parameters": params}


def _gem_result(cid, output):               # Gemini CLI stream-json tool_result
    return {"type": "tool_result", "timestamp": TS, "tool_id": cid, "status": "success", "output": output}


def _gem_shell(stdout):                     # run_shell_command's model-facing output (llmContent, wrapped)
    return f"<untrusted_context>\nOutput: {stdout}\n</untrusted_context>"


def _gem_response(cid, name, output):       # a functionResponse part
    return {"functionResponse": {"id": cid, "name": name, "response": {"output": output}}}


def _gem_call(cid, name, args, output, display=""):
    """One toolCalls entry of a Gemini session message: the call and its result in one object."""
    return {"id": cid, "name": name, "args": args, "result": [_gem_response(cid, name, output)], "status": "success",
            "timestamp": TS, "resultDisplay": display, "displayName": name, "description": "",
            "renderOutputAsMarkdown": False}


def _gem_message(mid, calls, content="", tokens=True):
    rec = {"id": mid, "timestamp": TS, "type": "gemini", "content": content, "toolCalls": calls, "thoughts": [],
           "model": "model-under-test"}
    if tokens:
        rec["tokens"] = {"input": 10, "output": 2, "cached": 0, "thoughts": 0, "tool": 0, "total": 12}
    return rec


GEM_HEAD = {"sessionId": "session-1", "projectHash": "hash-1", "startTime": TS, "lastUpdated": TS}
GEM_USER = {"id": "msg-u1", "timestamp": TS, "type": "user", "content": [{"text": "read the pinned versions"}]}


def _cx_item(event, iid, command, output, status="completed"):     # codex exec --json command_execution
    item = {"id": iid, "type": "command_execution", "command": command, "aggregated_output": output,
            "exit_code": 0 if status == "completed" else None, "status": status}
    return {"type": event, "item": item}


def _cx_wrap(script, shell="/bin/bash"):     # the presentation string: shlex_join([shell, "-lc", script])
    return f"{shell} -lc '{script}'"


def _cx_line(n, kind, payload):              # one rollout line
    return {"timestamp": TS, "ordinal": n, "type": kind, "payload": payload}


def _cx_meta():
    return _cx_line(0, "session_meta", {"id": "thread-1", "cli_version": "0.162.1", "history_mode": "paginated"})


def _cx_call(n, cid, script, name="exec_command"):
    return _cx_line(n, "response_item", {"type": "function_call", "name": name,
                                         "arguments": json.dumps({"cmd": script}, ensure_ascii=False),
                                         "call_id": cid})


def _cx_output(n, cid, stdout, items=False):
    text = f"Chunk ID: 1a2b3c\nWall time: 0.0105 seconds\nProcess exited with code 0\nOutput:\n{stdout}"
    return _cx_line(n, "response_item", {"type": "function_call_output", "call_id": cid,
                                         "output": [{"type": "input_text", "text": text}] if items else text})


def _cx_end(n, cid, argv, stdout):
    # round 4: the keys of the committed arm O rollouts' CommandExecution items (census, key names only), source
    # unified_exec_startup; every value invented here
    return _cx_line(n, "event_msg", {"type": "item_completed", "thread_id": "thread-1", "turn_id": "turn-1",
                                     "item": {"type": "CommandExecution", "id": cid, "command": argv,
                                              "cwd": "/run/gars", "parsed_cmd": [], "process_id": "1001",
                                              "source": "unified_exec_startup", "status": "completed",
                                              "aggregated_output": stdout, "exit_code": 0}})


# Round 4 (glitch-26's B17-16c): arm O's code-mode records, in the census's shape (key names and value types only; no
# record text copied): a custom_tool_call `exec` whose input is a script string, and its custom_tool_call_output, a list
# of input_text items.
EXEC_INPUT = 'const r = await tools.exec_command({cmd: "cat _references/environment.md"});\ntext(r.output);'


def _cx_custom(n, cid, name="exec", inp=EXEC_INPUT):
    return _cx_line(n, "response_item", {"type": "custom_tool_call", "name": name, "call_id": cid, "id": f"ctc_{n}",
                                         "input": inp, "status": "completed"})


def _cx_custom_out(n, cid, text):
    return _cx_line(n, "response_item", {"type": "custom_tool_call_output", "call_id": cid, "id": f"ctco_{n}",
                                         "output": [{"type": "input_text", "text": text}]})


# Round 2 (glitch-26's ruling B17-5): each arm's read shapes live with its adapter and reach the scan through
# read_shapes; read here so a missing record makes the shape tests red, never this module's import.
import gemini_adapter as _gemini_adapter  # noqa: E402
import codex_adapter as _codex_adapter  # noqa: E402

GEM_SHAPES = getattr(_gemini_adapter, "READ_SHAPES", ())
CODEX_SHAPES = getattr(_codex_adapter, "READ_SHAPES", ())


class TestOD57OtherArms(TestOD57Ruling):
    """B17-2: each Gemini and Codex record shape in which an agent's read of the ruled doc carries the line back to the
    model, in the turn stream and in the native session file (red on 67075247 by design), and the refusals every fix
    keeps: the line in the model's own text, in a call's arguments, in a read of another file, and in a result whose
    call id is missing or names two calls."""

    def stdout(self, how):
        return {"cat": f"line before\n{self.text}\nline after\n", "grep-n": f"175:{self.text}\n",
                "grep": f"{self.text}\n"}[how]

    def read_shapes(self):
        """The arm's read shapes, as the drive passes them for its arm's take: by the test's name (a data witness of
        round 3 sets shapes_override for one scan)."""
        if getattr(self, "shapes_override", None) is not None:
            return self.shapes_override
        name = self._testMethodName
        return GEM_SHAPES if "gemini" in name else CODEX_SHAPES if "codex" in name else ()

    def scan(self, files, scanner=None):
        scanner = scanner or _Gitleaks(self.text[:40])
        return sr.scan(files, SECRETS, rules_scanner=scanner, read_shapes=self.read_shapes()), scanner

    def scanned(self, name, body, kind):
        p = self.write(name, body)
        r, _ = self.scan([(p, kind)])
        return p, r

    def assert_admitted(self, name, body, kind, lines):
        p, r = self.scanned(name, body, kind)
        self.assertEqual(r["refused"], [])
        self.assertEqual(r["ruled"], [{"path": p, "line": n, "rule": OD57_RULE, "ruling": "OD57"} for n in lines])

    def assert_refused(self, name, body, kind, lines):
        p, r = self.scanned(name, body, kind)
        self.assertEqual(r["ruled"], [])
        self.assertEqual([(x["line"], x["why"]) for x in r["refused"]],
                         [(n, f"the rules scanner's rule {OD57_RULE!r}") for n in lines])

    def assert_line_retargeted(self, name, body, kind, lines):
        """od57-line: a refusal on `lines` that the widening admits there, retargeted (TestOD57Ruling.od57_line)."""
        self.od57_line(lambda b: self.assert_refused(name, b, kind, lines),
                       lambda b: self.assert_admitted(name, b, kind, lines), body)

    # ---- Gemini CLI 0.64.0, the turn stream (stream-json): run_shell_command's output is its stdout; read_file's is
    # a summary string that never carries the file's text (design note, section 1)
    def test_gemini_stream_shell_reads_are_admitted(self):
        for how, cmd in SHELL_READS:
            with self.subTest(how=how):
                body = _cc({"type": "init", "timestamp": TS, "session_id": "session-1", "model": "model-under-test"},
                           _gem_use("call-g1", "run_shell_command", {"command": cmd, "description": "read the doc"}),
                           _gem_result("call-g1", self.stdout(how).rstrip("\n")))
                self.assert_admitted(f"turn-1-{how}.jsonl", body, "stream", [3])

    # ---- Gemini CLI 0.64.0, the native session file (chats/*.jsonl)
    def test_gemini_session_tool_calls_are_admitted(self):
        doc = "/tmp/run-c8021046/gars/" + DOC_REL
        reads = [(how, "run_shell_command", {"command": cmd}, _gem_shell(self.stdout(how).rstrip("\n")),
                  self.stdout(how).rstrip("\n")) for how, cmd in SHELL_READS]
        reads.append(("read_file", "read_file", {"file_path": doc}, f"line before\n{self.text}\nline after", ""))
        for how, name, args, output, display in reads:
            with self.subTest(how=how):
                body = _cc(GEM_HEAD, GEM_USER, _gem_message("msg-g1", [_gem_call("call-g1", name, args, output,
                                                                                   display)]))
                self.assert_admitted(f"session-{how}.jsonl", body, "session", [3])

    def test_gemini_session_reappended_message_is_admitted(self):
        """The writer appends the whole message again on each update (its tokens here): the same call, twice."""
        call = _gem_call("call-g1", "run_shell_command", {"command": SHELL_READS[0][1]},
                         _gem_shell(self.stdout("cat").rstrip("\n")), self.stdout("cat").rstrip("\n"))
        body = _cc(GEM_HEAD, GEM_USER, _gem_message("msg-g1", [call], tokens=False), _gem_message("msg-g1", [call]))
        self.assert_admitted("session-reappended.jsonl", body, "session", [3, 4])

    def test_gemini_session_function_response_and_patch_are_admitted(self):
        name, args = "run_shell_command", {"command": SHELL_READS[1][1]}
        output = _gem_shell(self.stdout("grep-n").rstrip("\n"))
        call = _gem_call("call-g1", name, args, output, self.stdout("grep-n").rstrip("\n"))
        cases = {
            "the function response turn": {"id": "msg-u2", "timestamp": TS, "type": "user",
                                           "content": [_gem_response("call-g1", name, output)]},
            "a $patch of the tool result": {"$patch": {"updates": [
                {"id": "msg-g1", "toolCalls": [{"id": "call-g1", "result": [_gem_response("call-g1", name, output)]}]}
            ]}},
        }
        for case, rec in cases.items():
            with self.subTest(case):
                body = _cc(GEM_HEAD, GEM_USER, _gem_message("msg-g1", [call]), rec)
                self.assert_admitted("session-response.jsonl", body, "session", [3, 4])

    def test_gemini_refusals(self):
        doc, other = "/tmp/run-c8021046/gars/" + DOC_REL, "/run/gars/_references/other.md"
        read = _gem_call("call-g1", "read_file", {"file_path": doc}, f"{self.text}\n")
        stream = {
            "own text": [{"type": "message", "timestamp": TS, "role": "assistant",
                          "content": f"the doc says:\n{self.text}\n"}],
            "call arguments": [_gem_use("call-g1", "write_file", {"file_path": "notes.md", "content": self.text}),
                               _gem_result("call-g1", "")],
            "another file": [_gem_use("call-g1", "run_shell_command", {"command": "cat _references/other.md"}),
                             _gem_result("call-g1", self.stdout("cat"))],
            "call id missing": [_gem_result("call-g9", self.stdout("grep"))],
            "call id twice": [_gem_use("call-g1", "run_shell_command", {"command": SHELL_READS[0][1]}),
                              _gem_use("call-g1", "run_shell_command", {"command": "cat _references/other.md"}),
                              _gem_result("call-g1", self.stdout("cat"))],
        }
        lines = {"own text": [1], "call arguments": [1], "another file": [2], "call id missing": [1],
                 "call id twice": [3]}
        for case, recs in stream.items():
            with self.subTest(file="stream", case=case):
                if case == "another file":       # od57-line: a whole line of run_shell_command's output (retargeted)
                    self.assert_line_retargeted("turn-1.jsonl", _cc(*recs), "stream", lines[case])
                else:
                    self.assert_refused("turn-1.jsonl", _cc(*recs), "stream", lines[case])
        session = {
            "own text": ([_gem_message("msg-g1", [], content=f"the doc says:\n{self.text}")], [2]),
            "own text beside a ruled read": ([_gem_message("msg-g1", [read], content=self.text)], [2]),
            "call arguments": ([_gem_message("msg-g1", [_gem_call("call-g1", "write_file",
                                                                  {"file_path": "notes.md", "content": self.text},
                                                                  "Successfully wrote notes.md")])], [2]),
            "another file": ([_gem_message("msg-g1", [_gem_call("call-g1", "read_file", {"file_path": other},
                                                                f"{self.text}\n")])], [2]),
            "call id missing": ([{"id": "msg-u2", "timestamp": TS, "type": "user", "content": [
                _gem_response("call-g9", "read_file", f"{self.text}\n")]}], [2]),
            "call id twice": ([_gem_message("msg-g1", [read]),
                               _gem_message("msg-g2", [_gem_call("call-g1", "read_file", {"file_path": other},
                                                                 f"{self.text}\n")])], [2, 3]),
            "no call id": ([_gem_message("msg-g1", [{k: v for k, v in read.items() if k != "id"}])], [2]),
        }
        for case, (recs, want) in session.items():
            with self.subTest(file="session", case=case):
                self.assert_refused("session.jsonl", _cc(GEM_HEAD, *recs), "session", want)

    # ---- Codex CLI 0.162.1, the turn stream (exec --json): command_execution items, the call and its output together
    def test_codex_stream_command_executions_are_admitted(self):
        # round 3 (glitch-26's B17-14): only the arm O image's shell, /bin/bash, wraps an admitted read; the zsh case of
        # rounds 1 and 2 is now TestB17Round3's refusal
        # lane vendor-b24 (design section 2, F-RS-6): -c is no longer admitted (no committed record uses it)
        cases = [(how, _cx_wrap(cmd)) for how, cmd in SHELL_READS] + [("-c", "/bin/bash -c 'cat " + DOC_REL + "'")]
        for how, command in cases:
            with self.subTest(how=how):
                out = self.stdout("cat" if how == "-c" else how)
                body = _cc({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
                           _cx_item("item.started", "item_1", command, "", "in_progress"),
                           _cx_item("item.completed", "item_1", command, out))
                if how == "-c":                  # od57-line: admitted whatever the flag (retargeted)
                    self.assert_line_retargeted(f"turn-1-{how}.jsonl", body, "stream", [4])
                else:
                    self.assert_admitted(f"turn-1-{how}.jsonl", body, "stream", [4])

    # ---- Codex CLI 0.162.1, the native session file (the rollout)
    def test_codex_rollout_reads_are_admitted(self):
        # round 4 (glitch-26's B17-16): the rollout in arm O's real shape, code mode: a custom_tool_call `exec`, the
        # CommandExecution its script ran (its own id, no function_call), and the exec's output holding a verbatim copy
        # of that command's output
        for how, cmd in SHELL_READS:
            with self.subTest(how=how):
                out = self.stdout(how)
                body = _cc(_cx_meta(), _cx_custom(1, "call-o1"),
                           _cx_end(2, "exec-cmd-1", ["/bin/bash", "-lc", cmd], out),
                           _cx_custom_out(3, "call-o1", f"Script completed\n{out}exit code 0"))
                self.assert_admitted(f"rollout-{how}.jsonl", body, "session", [3, 4])

    def test_codex_refusals(self):
        start = ({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"})
        other = "cat _references/other.md"
        stream = {
            "own text": ([{"type": "item.completed", "item": {"id": "item_1", "type": "agent_message",
                                                               "text": f"the doc says:\n{self.text}\n"}}], [3]),
            "call arguments": ([_cx_item("item.completed", "item_1", _cx_wrap(f"echo {self.text}"), "")], [3]),
            "another file": ([_cx_item("item.completed", "item_1", _cx_wrap(other), self.stdout("cat"))], [3]),
            "call id missing": ([{"type": "item.completed", "item": {
                k: v for k, v in _cx_item("item.completed", "x", _cx_wrap(SHELL_READS[0][1]),
                                          self.stdout("cat"))["item"].items() if k != "id"}}], [3]),
            "call id twice": ([_cx_item("item.completed", "item_1", _cx_wrap(SHELL_READS[0][1]), self.stdout("cat")),
                               _cx_item("item.completed", "item_1", _cx_wrap(other), "elsewhere\n")], [3]),
            "started as another command": ([_cx_item("item.started", "item_1", _cx_wrap(other), "", "in_progress"),
                                            _cx_item("item.completed", "item_1", _cx_wrap(SHELL_READS[0][1]),
                                                     self.stdout("cat"))], [4]),
        }
        for case, (recs, want) in stream.items():
            with self.subTest(file="stream", case=case):
                if case == "another file":       # od57-line: a whole line of the shell's output (retargeted)
                    self.assert_line_retargeted("turn-1.jsonl", _cc(*start, *recs), "stream", want)
                else:
                    self.assert_refused("turn-1.jsonl", _cc(*start, *recs), "stream", want)
        nested = "sh -c 'cat _references/environment.md'"
        rollout = {
            "own text": ([_cx_line(1, "response_item", {"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": f"the doc says:\n{self.text}\n"}]})], [2]),
            "call arguments": ([_cx_call(1, "call-o1", f"echo {self.text}"), _cx_output(2, "call-o1", "")], [2]),
            "another file": ([_cx_call(1, "call-o1", other), _cx_output(2, "call-o1", self.stdout("cat"))], [3]),
            "call id missing": ([_cx_output(1, "call-o9", self.stdout("cat"))], [2]),
            "call id twice": ([_cx_call(1, "call-o1", SHELL_READS[0][1]), _cx_call(2, "call-o1", other),
                               _cx_output(3, "call-o1", self.stdout("cat"))], [4]),
            "a shell inside the script": ([_cx_call(1, "call-o1", nested),
                                           _cx_end(2, "call-o1", ["/bin/bash", "-lc", nested], self.stdout("cat")),
                                           _cx_output(3, "call-o1", self.stdout("cat"))], [3, 4]),
            "a tool that is not the shell": ([_cx_line(1, "response_item", {
                "type": "function_call", "name": "write_stdin", "arguments": json.dumps({"session_id": 1, "chars": ""}),
                "call_id": "call-o1"}), _cx_output(2, "call-o1", self.stdout("cat"))], [3]),
        }
        for case, (recs, want) in rollout.items():
            with self.subTest(file="rollout", case=case):
                if case == "a shell inside the script":
                    # od57-line: the CommandExecution's whole output line is admitted (line 3); the function_call
                    # output (line 4) is no shape's shell tool and still refuses. Retargeted: the read rules alone
                    # refuse both, and a byte after the pinned bytes refuses both
                    body = _cc(_cx_meta(), *recs)
                    p, r = self.scanned("rollout.jsonl", body, "session")
                    self.assertEqual(([x["line"] for x in r["ruled"]], [x["line"] for x in r["refused"]]), ([3], [4]))
                    with self.reads_only():
                        self.assert_refused("rollout.jsonl", body, "session", want)
                    self.assert_refused("rollout.jsonl", self.line_twin(body), "session", want)
                else:
                    self.assert_refused("rollout.jsonl", _cc(_cx_meta(), *recs), "session", want)


for _name in [n for n in vars(TestOD57Ruling) if n.startswith("test_")]:
    setattr(TestOD57OtherArms, _name, None)  # the parent's tests run once, in the parent


# ------------------------------------------------------------------------------------------------- B17, round 2
# glitch-26's rulings B17-5 to B17-9 (lane vendor-b17 round 2, 19 Oct 2026): the empty default admits exactly what it
# did before; a session call found by its id only when every copy is the same call (B17-6); grep_search, PTY (CRLF)
# output, write_stdin and zsh -lfc stay refused (B17-7); each admission conjunct has a witness that goes red alone; the
# drive passes each row's arm's shapes at its three scan calls, registered as piece B17 of check_vendor_sources.
OTHER = "cat _references/other.md"


class TestB17ReadShapes(TestOD57OtherArms):
    """Round 2: the default, the schema, B17-6 and B17-7's refusals, and one witness per admission conjunct."""

    def witness(self, label, name, body, kind, lines, fn, *edits, line=False):
        """Refused as is, on `lines`; admitted on exactly those lines with only `edits` made to sr.<fn>. With `line`
        (od57-line, retargeted): admitted as is and refused with a byte after the pinned bytes, the witness itself
        held on the read rules alone (the fallback off)."""
        if line:
            self.assert_admitted(name, body, kind, lines)
            self.assert_refused(name, self.line_twin(body), kind, lines)
            with self.reads_only():
                self.assert_refused(name, body, kind, lines)
                with _mutant(fn, *edits):
                    self.assert_admitted(name, body, kind, lines)
            red(f"B17 {label}")
            return
        self.assert_refused(name, body, kind, lines)
        with _mutant(fn, *edits):
            self.assert_admitted(name, body, kind, lines)
        red(f"B17 {label}")

    def shell_call(self, cid="call-g1", command=SHELL_READS[0][1], output="", display=""):
        return _gem_call(cid, "run_shell_command", {"command": command}, output, display)

    # ---- the default and the schema
    def test_the_arms_hold_read_shapes(self):
        for shapes in (GEM_SHAPES, CODEX_SHAPES):
            self.assertIsInstance(shapes, tuple)
            self.assertTrue(shapes)
            p = self.write("plain.jsonl", _cc({"type": "assistant", "text": "nothing ruled"}))
            r = sr.scan([(p, "transcript")], SECRETS, rules_scanner=no_findings, read_shapes=shapes)
            self.assertEqual((r["refused"], r["ruled"]), ([], []))

    def test_empty_read_shapes_give_todays_results(self):
        """B17-5: every OD57 fixture of TestOD57Ruling scans the same with read_shapes=() as with no argument."""
        doc = "_references/environment.md"
        bodies = [self.read_record(), self.read_record(sidechain=True), self.read_record(_one_char_off(self.text)),
                  self.bash_record(f"cat {doc}", f"line before\n{self.text}\nline after\n"),
                  self.bash_record(f"grep -n pinned {doc}", f"175:{self.text}\n", True),
                  self.bash_record(f"sed -n 175p {doc}", self.text + "\n"),
                  self.bash_record(W167, f"{doc}:175:{self.text}\n"),
                  _cc({"type": "assistant", "message": {"content": [{"type": "text", "text": self.text}]}}),
                  _cc(_result("toolu_X", f"175\t{self.text}"))]
        for i, body in enumerate(bodies):
            for kind in ("transcript", "stream", "session", "ledger"):
                with self.subTest(body=i, kind=kind):
                    p = self.write(f"{kind}-{i}.jsonl", body)
                    before = sr.scan([(p, kind)], SECRETS, rules_scanner=_Gitleaks(self.text[:40]))
                    after = sr.scan([(p, kind)], SECRETS, rules_scanner=_Gitleaks(self.text[:40]), read_shapes=())
                    self.assertEqual(after, before)

    def test_a_shape_off_its_schema_refuses(self):
        p = self.write("plain.jsonl", _cc({"type": "assistant", "text": "nothing ruled"}))
        good = GEM_SHAPES[0]
        bad = [dict(good, extra=1), {k: v for k, v in good.items() if k != "copies"}, dict(good, copies="many"),
               dict(good, tools={}), dict(good, call=dict(good["call"], match=None)), "a shape", None]
        for i, shape in enumerate(bad):
            with self.subTest(i=i):
                with self.assertRaises(sr.ScanError):
                    sr.scan([(p, "transcript")], SECRETS, rules_scanner=no_findings, read_shapes=(shape,))
        with self.assertRaises(sr.ScanError):
            sr.scan([(p, "transcript")], SECRETS, rules_scanner=no_findings, read_shapes=good)

    # ---- B17-6: one call per id in a session file
    def test_gemini_session_two_calls_under_one_id_refuse(self):
        out = _gem_shell(self.stdout("cat").rstrip("\n"))
        body = _cc(GEM_HEAD, _gem_message("msg-g1", [self.shell_call(output=out)]),
                   _gem_message("msg-g2", [self.shell_call(command=SHELL_READS[1][1], output=out)]))
        self.witness("B17-6: two calls under one id", "session-two.jsonl", body, "session", [2, 3], "_shape_read",
                     ("any(g != got[0] for g in got)", "False"))

    # ---- B17-7: what stays refused
    def test_gemini_session_grep_search_refuses(self):
        call = _gem_call("call-g1", "grep_search", {"pattern": "pinned", "dir_path": "_references"}, f"{self.text}\n")
        self.assert_refused("session-grep.jsonl", _cc(GEM_HEAD, _gem_message("msg-g1", [call])), "session", [2])

    def test_codex_pty_output_refuses(self):
        crlf = self.stdout("cat").replace("\n", "\r\n")
        cmd = SHELL_READS[0][1]
        stream = _cc({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
                     _cx_item("item.completed", "item_1", _cx_wrap(cmd), crlf))
        self.assert_refused("turn-1.jsonl", stream, "stream", [3])
        rollout = _cc(_cx_meta(), _cx_call(1, "call-o1", cmd), _cx_end(2, "call-o1", ["/bin/bash", "-lc", cmd], crlf),
                      _cx_output(3, "call-o1", crlf))
        self.assert_refused("rollout.jsonl", rollout, "session", [3, 4])

    def test_codex_write_stdin_refuses(self):
        """write_stdin's output refuses, even with a read's script in its arguments. Round 4 (B17-16d): arm O has no
        function_call shape at all, so the tool binding's witness is TestB17Round4's custom tool name test."""
        body = _cc(_cx_meta(), _cx_line(1, "response_item", {
            "type": "function_call", "name": "write_stdin", "call_id": "call-o1",
            "arguments": json.dumps({"session_id": 1, "cmd": SHELL_READS[0][1]})}),
            _cx_output(2, "call-o1", self.stdout("cat")))
        self.assert_refused("rollout.jsonl", body, "session", [3])

    def test_codex_zsh_lfc_refuses(self):
        # round 3: the flag alone holds it (the image's own shell, /bin/bash, with zsh's brokered -lfc flag)
        command = "/bin/bash -lfc 'cat _references/environment.md'"
        body = _cc({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
                   _cx_item("item.completed", "item_1", command, self.stdout("cat")))
        self.witness("the wrapper's flag", "turn-1.jsonl", body, "stream", [3], "_ruled_wrapped",
                     ("argv[1] not in flags", "False"), line=True)

    # ---- one witness per admission conjunct
    def test_gemini_witness_the_path_names_the_doc(self):
        call = _gem_call("call-g1", "read_file", {"file_path": "/run/gars/_references/other.md"}, f"{self.text}\n")
        self.witness("the read's path", "session.jsonl", _cc(GEM_HEAD, _gem_message("msg-g1", [call])), "session",
                     [2], "_reads_doc", ('return dict(tool) if _resolves_to_doc(arg) else None', 'return dict(tool)'))

    def test_gemini_witness_the_script_reads_the_doc(self):
        call = self.shell_call(command=OTHER, output=_gem_shell(self.stdout("cat").rstrip("\n")))
        self.witness("the script", "session.jsonl", _cc(GEM_HEAD, _gem_message("msg-g1", [call])), "session", [2],
                     "_reads_doc", ("spec = _ruled_shell(arg)", 'spec = _ruled_shell("cat " + _RULED_DOC)'), line=True)

    def test_codex_witness_the_wrapper_has_three_words(self):
        # round 3: a CommandExecution item's call is its function_call (B17-12), so the rollout carries it
        body = _cc(_cx_meta(), _cx_call(1, "call-o1", SHELL_READS[0][1]),
                   _cx_end(2, "call-o1", ["/bin/bash", "-lc", SHELL_READS[0][1], "x"], self.stdout("cat")))
        self.witness("the wrapper's length", "rollout.jsonl", body, "session", [3], "_ruled_wrapped",
                     ("len(argv) == 3", "len(argv) >= 3"), line=True)

    def test_codex_witness_the_wrapper_is_a_shell(self):
        for shell in ("/usr/bin/fish", "/tmp/x/bash", "bash", "/bin/zsh", "/bin/sh"):
            with self.subTest(shell=shell):
                body = _cc(_cx_meta(), _cx_call(1, "call-o1", SHELL_READS[0][1]),
                           _cx_end(2, "call-o1", [shell, "-lc", SHELL_READS[0][1]], self.stdout("cat")))
                self.witness("the wrapper's shell", "rollout.jsonl", body, "session", [3], "_ruled_wrapped",
                             ("argv[0] not in shells", "False"), line=True)

    def test_gemini_witness_a_stream_call_is_found_once(self):
        use = _gem_use("call-g1", "run_shell_command", {"command": SHELL_READS[0][1]})
        body = _cc(use, use, _gem_result("call-g1", self.stdout("cat")))
        self.witness("a stream call found once", "turn-1.jsonl", body, "stream", [3], "_shape_read",
                     ('shape["copies"] == "one" and len(got) != 1', "False"))

    def test_gemini_witness_a_response_names_its_call(self):
        part = _gem_response("call-g1", "read_file", f"{self.text}\n")
        body = _cc(GEM_HEAD, _gem_message("msg-g1", [self.shell_call()]),
                   {"id": "msg-u2", "timestamp": TS, "type": "user", "content": [part]})
        self.witness("a response's name", "session.jsonl", body, "session", [3], "_shape_read",
                     ("name is not None and name != got[0][0]", "False"))

    def test_gemini_witness_a_joined_result_is_its_own_call(self):
        body = _cc(GEM_HEAD, _gem_message("msg-g1", [self.shell_call()]),
                   _gem_message("msg-g2", [{"id": "call-g1", "resultDisplay": f"{self.text}\n"}]))
        self.witness("a joined result is a copy of its call", "session.jsonl", body, "session", [3],
                     "_shape_strings", ("if joined and _shape_call(node, spec) is None:", "if False:"))

    def test_gemini_witness_the_prefix_is_on_the_first_line_only(self):
        out = f"<untrusted_context>\nOutput: line before\nOutput: {self.text}\n</untrusted_context>"
        body = _cc(GEM_HEAD, _gem_message("msg-g1", [self.shell_call(output=out)]))
        self.witness("the prefix's line", "session.jsonl", body, "session", [2], "_line_prefix",
                     ("i == first", "True"))


class TestB17Wiring(unittest.TestCase):
    """B17-5: the drive passes each row's arm's shapes at its three scan calls, and check_vendor_sources registers the
    drive.py edit as piece B17 (its exact lines, the rest of drive.py held by piece EB as before)."""

    def drive(self):
        import drive
        return drive

    def test_scan_read_shapes_by_arm(self):
        d = self.drive()
        cases = [({"arm": "G"}, GEM_SHAPES), ({"arm": "O"}, CODEX_SHAPES), ({"arm": "A"}, ()), ({"arm": "C"}, ()),
                 ({}, ()), (None, ()), ({"arm": "G", "agent": {"harness": "gemini"}}, GEM_SHAPES),
                 ({"arm": "O", "agent": {"harness": "codex"}}, CODEX_SHAPES),
                 ({"arm": "G", "agent": {"harness": "codex"}}, ()), ({"arm": "O", "agent": {"harness": "claude-code"}}, ())]
        for row, want in cases:
            with self.subTest(row=row):
                self.assertEqual(d.scan_read_shapes(row), want)

    def test_every_scan_call_passes_its_rows_shapes(self):
        import ast
        src = Path(STUDY, "drive.py").read_text(encoding="utf-8")
        calls = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr in ("scan", "scan_with_witness") and isinstance(n.func.value, ast.Name)
                 and n.func.value.id == "_scan_record"]
        self.assertEqual(len(calls), 3)
        for c in calls:
            kw = [k for k in c.keywords if k.arg == "read_shapes"]
            self.assertEqual(len(kw), 1)
            v = kw[0].value
            self.assertTrue(isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "scan_read_shapes"
                            and len(v.args) == 1 and isinstance(v.args[0], ast.Name)
                            and v.args[0].id in ("row", "entry"), ast.dump(v))

    def test_piece_b17_holds_the_drive_edit(self):
        import check_vendor_sources as cvs
        src = Path(STUDY, "drive.py").read_text(encoding="utf-8")
        self.assertEqual(cvs.problems("B17", ["drive.py", "box/scan_record.py", "gemini_adapter.py",
                                              "codex_adapter.py", "tests/test_scan_record.py"]), [])
        self.assertNotEqual(cvs.problems("P2", ["drive.py"]), [])
        self.assertEqual(cvs.edit_b_problems(src), [])
        line = "read_shapes=scan_read_shapes(row),"
        self.assertEqual(src.count(line), 2)
        mutants = {
            "a keyword line changed": src.replace(line, "read_shapes=_gemini.READ_SHAPES,", 1),
            "a keyword line dropped": src.replace(" " * 33 + line + "\n", "", 1),
            "the helper changed": src.replace("return module.READ_SHAPES if declared == harness else ()",
                                              "return module.READ_SHAPES", 1),
            "another line moved": src.replace("VENDOR_HARNESSES = (\"codex\", \"gemini\")",
                                              "VENDOR_HARNESSES = (\"codex\", \"gemini\", \"claude-code\")", 1),
        }
        for name, text in mutants.items():
            with self.subTest(mutant=name):
                self.assertNotEqual(text, src)
                self.assertNotEqual(cvs.b17_problems(text) + cvs.edit_b_problems(text), [], name)


# ------------------------------------------------------------------------------------------------- B17, round 3
# glitch-26's rulings B17-10 to B17-14 on review REVIEW-vendor-b17-a051f6e3 (19 Oct 2026): every node bound to its fixed
# record position, never found at any depth, on the read shapes (B17-10) and on the Claude path (B17-11); exec_command's
# shell argument checked (B17-12); each named refusal with a test and a witness, a tty output refused whatever its line
# ending (B17-13); the image's pinned shells only and run_shell_command's resultDisplay only (B17-14). A data witness
# widens one shape's positions, tools or prefix for one scan; it admits exactly the refused lines.
def _widened(shapes, index, part, **changes):
    """A copy of `shapes` whose shape `index` has its `part` ("call", "result" or the shape itself) changed."""
    out = [dict(s) for s in shapes]
    if part is None:
        out[index].update(changes)
    else:
        out[index][part] = dict(out[index][part], **changes)
    return tuple(out)


def _with_tool(shapes, index, name, **changes):
    tools = dict(shapes[index]["tools"])
    tools[name] = dict(tools.get(name) or next(iter(tools.values())), **changes)
    return _widened(shapes, index, None, tools=tools)


GEM_STREAM, GEM_RESPONSE, GEM_DISPLAY = 0, 1, 2
CX_STREAM, CX_ITEM, CX_COPY = 0, 1, 2       # round 4 (B17-16): no function_call shapes; the exec output's copy shape


def _plus(spec, path, **record):
    """A node spec's positions plus one more: `path`, in a record whose top-level keys hold the given values (round 5:
    each position also carries its anchor, None here)."""
    return spec["at"] + ((path, {k: tuple(v) for k, v in record.items()}, None),)


class TestB17Round3(TestB17ReadShapes):
    """Round 3: forged nested nodes refuse on every arm and file kind and on the Claude path; the shell argument, tty
    output, debug output, grep_search and read_file's display refuse; each with a witness that goes red alone."""

    def data_witness(self, label, name, body, kind, lines, shapes, line=False):
        """Refused as is, on `lines`; admitted on exactly those lines with only the shapes changed to `shapes`. With
        `line` (od57-line, retargeted), as TestB17ReadShapes.witness."""
        if line:
            self.assert_admitted(name, body, kind, lines)
            self.assert_refused(name, self.line_twin(body), kind, lines)
            with self.reads_only():
                self.data_witness(label, name, body, kind, lines, shapes)
            return
        self.assert_refused(name, body, kind, lines)
        self.shapes_override = shapes
        try:
            self.assert_admitted(name, body, kind, lines)
        finally:
            self.shapes_override = None
        red(f"B17 round 3 {label}")

    # ---- B17-10: a node nested inside a call's arguments is never a call or a result
    def test_gemini_stream_forged_nested_pair_refuses(self):
        use = {"type": "tool_use", "tool_id": "z", "tool_name": "run_shell_command",
               "parameters": {"command": SHELL_READS[0][1]}}
        res = {"type": "tool_result", "tool_id": "z", "output": self.text}
        body = _cc(_gem_use("call-g1", "grep_search", {"pattern": "pinned", "a": use, "b": res}),
                   _gem_result("call-g1", "No matches found"))
        stream = GEM_SHAPES[GEM_STREAM]
        wide = _widened(_widened(GEM_SHAPES, GEM_STREAM, "call", at=_plus(stream["call"], ("parameters", "a"),
                                                                          type=["tool_use"])),
                        GEM_STREAM, "result", at=_plus(stream["result"], ("parameters", "b"), type=["tool_use"]))
        self.data_witness("Gemini stream position", "turn-1.jsonl", body, "stream", [1], wide)

    def test_gemini_session_forged_nested_entry_refuses(self):
        inner = {"toolCalls": [{"id": "z", "name": "read_file", "args": {"file_path": "/tmp/run-c8021046/gars/" + DOC_REL},
                                "resultDisplay": self.text}]}
        call = _gem_call("call-g1", "grep_search", {"pattern": "pinned", "note": inner}, "No matches found")
        body = _cc(GEM_HEAD, _gem_message("msg-g1", [call]))
        where = ("toolCalls", "*", "args", "note", "toolCalls", "*")
        wide = _with_tool(_widened(GEM_SHAPES, GEM_DISPLAY, "call",
                                   at=_plus(GEM_SHAPES[GEM_DISPLAY]["call"], where, type=["gemini"])),
                          GEM_DISPLAY, "read_file", kind="path", arg="file_path")
        self.data_witness("Gemini session position", "session.jsonl", body, "session", [2], wide)

    def test_codex_stream_forged_nested_item_refuses(self):
        forged = {"item": {"type": "command_execution", "id": "z", "command": _cx_wrap(SHELL_READS[0][1]),
                           "aggregated_output": self.text}}
        body = _cc({"type": "thread.started", "thread_id": "thread-1"},
                   {"type": "item.completed", "item": {"id": "item_1", "type": "mcp_tool_call", "server": "s",
                                                       "tool": "t", "arguments": forged, "result": None,
                                                       "error": None, "status": "completed"}})
        wide = _widened(CODEX_SHAPES, CX_STREAM, "call", at=_plus(CODEX_SHAPES[CX_STREAM]["call"],
                                                                   ("item", "arguments", "item"), type=["item.completed"]))
        self.data_witness("Codex stream position", "turn-1.jsonl", body, "stream", [2], wide)

    def test_codex_rollout_forged_nested_pair_refuses(self):
        # round 4 (B17-16a): the rollout's CommandExecution is a joined shape again; the forged one sits in another
        # item's arguments
        cmd = SHELL_READS[0][1]
        forged = {"item": {"type": "CommandExecution", "id": "call-z", "command": ["/bin/bash", "-lc", cmd],
                           "aggregated_output": self.text}}
        body = _cc(_cx_meta(), _cx_line(1, "event_msg", {"type": "item_completed", "thread_id": "thread-1",
                                                          "turn_id": "turn-1", "item": {
                                                              "type": "McpToolCall", "id": "x", "arguments": forged}}))
        wide = _widened(CODEX_SHAPES, CX_ITEM, "call", at=_plus(CODEX_SHAPES[CX_ITEM]["call"],
                                                                 ("payload", "item", "arguments", "item"),
                                                                 type=["event_msg"]))
        self.data_witness("Codex rollout position", "rollout.jsonl", body, "session", [2], wide)

    # ---- B17-11: the Claude path reads only the message records' own top-level blocks
    def test_claude_forged_nested_pair_refuses(self):
        inp = {"x": {"type": "tool_use", "id": "z", "name": "Read", "input": {"file_path": self.doc}},
               "y": {"type": "tool_result", "tool_use_id": "z", "content": self.text}}
        body = _cc({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "toolu_1", "name": "Write",
                                                                  "input": inp}]}})
        p = self.write("transcript.jsonl", body)
        r = sr.scan([(p, "transcript")], SECRETS, rules_scanner=_Gitleaks(self.text[:40]))
        self.assertEqual((r["ruled"], [x["line"] for x in r["refused"]]), ([], [1]))
        from box import od57_rule
        with mock.patch.object(od57_rule, "_CLAUDE_AT", sr._CLAUDE_AT + (("message", "content", "*", "input", "x"),
                                                                        ("message", "content", "*", "input", "y"))):
            r = sr.scan([(p, "transcript")], SECRETS, rules_scanner=_Gitleaks(self.text[:40]))
        self.assertEqual(([x["line"] for x in r["ruled"]], r["refused"]), ([1], []))
        red("B17 round 3 Claude position")

    # ---- B17-12: exec_command's shell argument. Round 4 (glitch-26's B17-16d): arm O's pinned models run code mode
    # only, so exec_command is never a direct function_call and no function_call shape remains; a function_call output
    # refuses whatever its shell, and the shell that ran is held by the CommandExecution's own argv (the wrapper's
    # shell witness, TestB17ReadShapes)
    def test_codex_exec_command_shell_argument(self):
        cmd = SHELL_READS[0][1]

        def body(args):
            return _cc(_cx_meta(), _cx_line(1, "response_item", {"type": "function_call", "name": "exec_command",
                                                                  "arguments": json.dumps(args), "call_id": "call-o1"}),
                       _cx_output(2, "call-o1", self.stdout("cat")))
        for shell in ("/bin/bash", "/usr/bin/fish", "/bin/zsh", "bash", "/tmp/x/bash"):
            with self.subTest(shell=shell):
                self.assert_refused("rollout.jsonl", body({"cmd": cmd, "shell": shell}), "session", [3])

    # ---- B17-13: each named refusal, with its witness
    def test_gemini_grep_search_refuses_with_witness(self):
        call = _gem_call("call-g1", "grep_search", {"pattern": "pinned", "dir_path": "/tmp/run-c8021046/gars/" + DOC_REL},
                         f"{self.text}\n")
        body = _cc(GEM_HEAD, _gem_message("msg-g1", [call]))
        wide = _with_tool(GEM_SHAPES, GEM_RESPONSE, "grep_search", kind="path", arg="dir_path", prefix=None,
                          opener=None)
        self.data_witness("grep_search", "session.jsonl", body, "session", [2], wide)

    def test_codex_pty_crlf_refuses_with_witness(self):
        crlf = self.stdout("cat").replace("\n", "\r\n")
        body = _cc({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
                   _cx_item("item.completed", "item_1", _cx_wrap(SHELL_READS[0][1]), crlf))
        self.witness("a PTY's CRLF line", "turn-1.jsonl", body, "stream", [3], "_line_text",
                     ('b = form.encode("utf-8", "surrogateescape")',
                      'b = form.rstrip("\\r").encode("utf-8", "surrogateescape")'))

    def test_codex_tty_output_refuses_whatever_its_line_ending(self):
        """Round 4 (B17-16): a tty exec's output in the code-mode rollout is held by its CRLF bytes, in the
        CommandExecution and in the exec's output copy; the `tty` argument now sits only inside the exec script's text,
        which no shape reads (a known limit, recorded in the lane file, as the stream's since round 3)."""
        cmd = SHELL_READS[0][1]
        crlf = self.stdout("cat").replace("\n", "\r\n")
        body = _cc(_cx_meta(), _cx_custom(1, "call-o1", inp=EXEC_INPUT.replace("})", ", tty: true})")),
                   _cx_end(2, "exec-cmd-1", ["/bin/bash", "-lc", cmd], crlf), _cx_custom_out(3, "call-o1", crlf))
        self.assert_refused("rollout.jsonl", body, "session", [3, 4])

    def test_gemini_debug_mode_output_refuses_with_witness(self):
        use = _gem_use("call-g1", "run_shell_command", {"command": SHELL_READS[2][1]})
        for out in (f"Output: {self.text}", f"<untrusted_context>\nOutput: {self.text}\n</untrusted_context>"):
            with self.subTest(wrapped="<" in out):
                wide = _with_tool(GEM_SHAPES, GEM_STREAM, "run_shell_command", prefix="Output: ",
                                  opener="<untrusted_context>")
                self.data_witness("debug-mode output", "turn-1.jsonl", _cc(use, _gem_result("call-g1", out)),
                                  "stream", [2], wide)

    # ---- B17-14: run_shell_command's resultDisplay only
    def test_gemini_read_file_display_refuses_with_witness(self):
        call = _gem_call("call-g1", "read_file", {"file_path": "/tmp/run-c8021046/gars/" + DOC_REL}, "", f"{self.text}\n")
        body = _cc(GEM_HEAD, _gem_message("msg-g1", [call]))
        wide = _with_tool(GEM_SHAPES, GEM_DISPLAY, "read_file", kind="path", arg="file_path")
        self.data_witness("read_file's display", "session.jsonl", body, "session", [2], wide)

    def test_the_image_shell_is_the_wrapper_shell(self):
        """B17-14: the one shell the arm O image names (box/codex/Dockerfile: useradd ... --shell /bin/bash dana)."""
        dockerfile = Path(STUDY, "box", "codex", "Dockerfile").read_text(encoding="utf-8")
        named = re.findall(r"--shell (\S+) dana\b", dockerfile)
        self.assertEqual(named, ["/bin/bash"])
        wrapped = [t for shape in CODEX_SHAPES for t in shape["tools"].values() if t["kind"] == "wrapped"]
        self.assertTrue(wrapped)
        for tool in wrapped:
            self.assertEqual(tool["shells"], tuple(named))


class TestB17Round3Wiring(unittest.TestCase):
    """B17-14: piece B17 binds `row` at the two row call sites and `entry` at the walk's, so a swap refuses."""

    def test_a_swapped_argument_refuses(self):
        import check_vendor_sources as cvs
        src = Path(STUDY, "drive.py").read_text(encoding="utf-8")
        self.assertEqual(cvs.b17_problems(src), [])
        row, entry = "read_shapes=scan_read_shapes(row),", "read_shapes=scan_read_shapes(entry),"
        swaps = {"the first row call passes entry": src.replace(row, entry, 1),
                 "the walk call passes row": src.replace(entry, row, 1)}
        for name, text in swaps.items():
            with self.subTest(name):
                self.assertNotEqual(text, src)
                self.assertNotEqual(cvs.b17_problems(text), [], name)
        red("B17 round 3 the call sites' argument names")


for _cls in (TestB17ReadShapes, TestB17Round3):
    for _name in [n for n in vars(TestOD57OtherArms) if n.startswith("test_")]:
        setattr(_cls, _name, None)           # TestOD57OtherArms' tests run once, in their own class
for _name in [n for n in vars(TestB17ReadShapes) if n.startswith("test_")]:
    setattr(TestB17Round3, _name, None)      # TestB17ReadShapes' tests run once, in their own class


# ------------------------------------------------------------------------------------------------- B17, round 4
# glitch-26's rulings B17-16a to B17-16d and NIT 2 on review REVIEW-vendor-b17-dd2d0398 (19 Oct 2026): arm O's real
# rollouts run code mode (a custom_tool_call `exec`, no function_call), so the rollout's CommandExecution admits on its
# own argv again (16a), and a custom_tool_call_output admits the ruled line only inside a verbatim copy of an admitted
# CommandExecution's aggregated_output in the same file, its call a custom_tool_call `exec` of the same id (16b); the
# fixtures are in the census's shape (16c); and each node's enclosing record must hold its type (NIT 2).
class TestB17Round4(TestB17Round3):
    """Round 4: arm O's code-mode rollout, each check with a witness that goes red alone."""

    def assert_split(self, name, body, kind, ruled, refused):
        p, r = self.scanned(name, body, kind)
        self.assertEqual([x["line"] for x in r["ruled"]], ruled)
        self.assertEqual([(x["line"], x["why"]) for x in r["refused"]],
                         [(n, f"the rules scanner's rule {OD57_RULE!r}") for n in refused])

    def code_mode(self, ce=None, call=None, out=None, cmd=SHELL_READS[0][1], argv=None, stdout=None):
        """meta, a custom_tool_call `exec`, its script's CommandExecution, the exec's output (each False leaves it out;
        round 5: `stdout` the read's output, the cat's by default)."""
        stdout = self.stdout("cat") if stdout is None else stdout
        recs = [_cx_meta()]
        if call is not False:
            recs.append(_cx_custom(len(recs), "call-o1", **(call or {})))
        if ce is not False:
            recs.append(_cx_end(len(recs), "exec-cmd-1", argv or ["/bin/bash", "-lc", cmd], stdout))
        if out is not False:
            text = f"Script completed\n{stdout}exit code 0" if out is None else out
            recs.append(_cx_custom_out(len(recs), "call-o1", text))
        return _cc(*recs)

    # ---- B17-16a: the CommandExecution alone
    def test_codex_command_execution_alone_is_admitted(self):
        self.assert_admitted("rollout.jsonl", self.code_mode(call=False, out=False), "session", [2])

    def test_codex_off_shape_command_execution_refuses(self):
        cmd = SHELL_READS[0][1]
        # od57-line: the CommandExecution's whole output line is admitted whatever its wrapper or script (retargeted)
        self.witness("16a the CommandExecution's -lc", "rollout.jsonl",
                     self.code_mode(call=False, out=False, argv=["/bin/bash", "-c", cmd]), "session", [2],
                     "_ruled_wrapped", ("argv[1] not in flags", "False"), line=True)
        for argv in (["/bin/bash", "-lc", OTHER], ["/bin/bash", "-lc", "sh -c '" + cmd + "'"]):
            with self.subTest(argv=argv[2]):
                self.assert_line_retargeted("rollout.jsonl", self.code_mode(call=False, out=False, argv=argv),
                                            "session", [2])

    # ---- B17-16b and 16c: the exec output's verbatim copy of an admitted read
    def test_codex_exec_output_copy_is_admitted(self):
        stdout = self.stdout("cat")
        for text in (stdout, f"Script completed\n{stdout}exit code 0", f"x{stdout}"):
            with self.subTest(text=text[:8]):
                self.assert_admitted("rollout.jsonl", self.code_mode(out=text), "session", [3, 4])

    def test_codex_exec_output_needs_an_admitted_read(self):
        # od57-line: the exec output is the shell's output copy, so its whole line is admitted with or without an
        # admitted read (retargeted)
        self.witness("16b an admitted read in the file", "rollout.jsonl", self.code_mode(ce=False), "session", [3],
                     "_copy_hits", ("for a, tool in srcs:", 'for a, tool in srcs + [(s, {"kind": "exact"})]:'),
                     line=True)
        self.assert_line_retargeted("rollout.jsonl", self.code_mode(cmd=OTHER), "session", [3, 4])

    def test_codex_exec_output_span_must_be_a_copy(self):
        stdout = self.stdout("cat")
        changed = stdout.replace("line after", "LINE AFTER")
        body = self.code_mode(out=f"Script completed\n{changed}exit code 0")
        # od57-line: the copy's whole line is admitted even where the span is no verbatim copy, and a byte after the
        # pinned bytes refuses both lines; the copy rule's witness holds on the read rules alone (retargeted)
        self.assert_split("rollout.jsonl", body, "session", [3, 4], [])
        self.assert_split("rollout.jsonl", self.line_twin(body), "session", [], [3, 4])
        with self.reads_only():
            self.assert_split("rollout.jsonl", body, "session", [3], [4])
            with _mutant("_copy_hits", ("s[p:p + len(a)] == a", "True")):
                self.assert_split("rollout.jsonl", body, "session", [3, 4], [])
        red("B17 16b the span is a verbatim copy")

    def test_codex_exec_output_needs_the_exec_tool(self):
        body = self.code_mode(call={"name": "wait"})
        self.assert_split("rollout.jsonl", body, "session", [3], [4])
        with _mutant("_shape_read", ('shape["tools"].get(got[0][0])', 'next(iter(shape["tools"].values()))')):
            self.assert_split("rollout.jsonl", body, "session", [3, 4], [])
        red("B17 16b the exec tool")

    def test_codex_exec_output_needs_its_call_id(self):
        body = _cc(_cx_meta(), _cx_custom(1, "call-o1"),
                   _cx_end(2, "exec-cmd-1", ["/bin/bash", "-lc", SHELL_READS[0][1]], self.stdout("cat")),
                   _cx_custom_out(3, "call-o9", f"Script completed\n{self.stdout('cat')}exit code 0"))
        self.assert_split("rollout.jsonl", body, "session", [3], [4])
        # round 5 (B17-19): the call is found by its id twice, for its tool and for its line (the copy's window)
        with _mutant("_shape_read", ("got = calls.get(cid)", "got = next(iter(calls.values()), None)")), \
                _mutant("_shape_strings", ('cl = call_lines.get(node[spec["id"]])',
                                           "cl = next(iter(call_lines.values()), None)")), \
                _mutant("_shape_calls", ("sum(1 for c, o in windows if c < n < o) == 1", "True")):
            # round 6 (B17-21): the window is the call id's too
            self.assert_split("rollout.jsonl", body, "session", [3, 4], [])
        red("B17 16b the call id")

    def test_codex_exec_output_admits_only_the_copy(self):
        stdout = self.stdout("cat")
        body = self.code_mode(out=f"Script completed\n{stdout}exit code 0\n{self.text}\n")
        self.assert_split("rollout.jsonl", body, "session", [3], [4])
        with _mutant("ruled_text", (DECODED_ELSEWHERE, "False"), (RAW_ELSEWHERE, "False")):
            self.assert_split("rollout.jsonl", body, "session", [3, 4], [])
        red("B17 16b nothing else in the output")

    def test_codex_function_call_shapes_are_gone(self):
        """B17-16d: arm O's records hold no function_call or function_call_output; no shape reads them."""
        for shape in CODEX_SHAPES:
            for spec in (shape["call"], shape["result"] or {}):
                self.assertNotIn(spec.get("match", {}).get("type"), ("function_call", "function_call_output"))

    # ---- NIT 2: the enclosing record's type
    def test_codex_stream_item_of_another_event_refuses(self):
        body = _cc({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
                   {"type": "turn.completed", "item": {"type": "command_execution", "id": "z",
                                                       "command": _cx_wrap(SHELL_READS[0][1]),
                                                       "aggregated_output": self.stdout("cat")}})
        wide = _widened(CODEX_SHAPES, CX_STREAM, "call", at=_plus(CODEX_SHAPES[CX_STREAM]["call"], ("item",),
                                                                   type=["turn.completed"]))
        self.data_witness("NIT 2 a stream item's event type", "turn-1.jsonl", body, "stream", [3], wide)

    def test_gemini_response_in_a_model_message_refuses(self):
        part = _gem_response("call-g1", "run_shell_command", _gem_shell(self.stdout("cat").rstrip("\n")))
        body = _cc(GEM_HEAD, _gem_message("msg-g1", [self.shell_call()]),
                   {"id": "msg-g2", "timestamp": TS, "type": "gemini", "content": [part]})
        wide = _widened(GEM_SHAPES, GEM_RESPONSE, "result",
                        at=_plus(GEM_SHAPES[GEM_RESPONSE]["result"], ("content", "*", "functionResponse"),
                                 type=["gemini"]))
        self.data_witness("NIT 2 a response's message type", "session.jsonl", body, "session", [3], wide)


for _cls_from in (TestOD57OtherArms, TestB17ReadShapes, TestB17Round3):
    for _name in [n for n in vars(_cls_from) if n.startswith("test_")]:
        setattr(TestB17Round4, _name, None)  # each earlier class's tests run once, in their own class


# ------------------------------------------------------------------------------------------------- B17, round 5
# glitch-26's rulings B17-17 to B17-19 and NITs 2, 3 and 5 on review REVIEW-vendor-b17-baef7c51 (19 Oct 2026):
# gpt-6.1-sol's exec output holds its read's output as one JSON string literal (census: 60 of 72; gpt-6-luna 32 of 36
# verbatim; the rest lossy middle truncations, refused); a position of the ruled line counts once, however many sources
# match it (B17-18); an exec output's sources are the reads between its own call's line and its line (B17-19); the
# CommandExecution's event is item_completed and its argv a list; no shape crosses file kinds; a functionResponse in an
# entry's result answers that entry.
def _sol(stdout):
    """gpt-6.1-sol's exec output item, in the census's shape: an object whose output is the read's output as one JSON
    string literal (key names and order invented; non-ASCII kept raw)."""
    return '{"exit_code":0,"output":' + json.dumps(stdout, ensure_ascii=False) + "}"


class TestB17Round5(TestB17Round4):
    """Round 5: each model's real exec output form, position counting, the exec pair's window, and the residual
    positions, each check with a witness that goes red alone."""

    def pair(self, cid, n, reads, out):
        """An exec call, its script's CommandExecutions (script, stdout), its output; from rollout line n + 1."""
        recs = [_cx_custom(n, cid)]
        for k, (script, stdout) in enumerate(reads):
            recs.append(_cx_end(n + 1 + k, f"{cid}-cmd-{k}", ["/bin/bash", "-lc", script], stdout))
        recs.append(_cx_custom_out(n + 1 + len(reads), cid, out))
        return recs

    # ---- B17-17: each model's real form
    def test_codex_each_models_exec_output_is_admitted(self):
        for how, cmd in SHELL_READS:
            stdout = self.stdout(how)
            for model, out in (("gpt-6-luna", stdout), ("gpt-6.1-sol", _sol(stdout))):
                with self.subTest(how=how, model=model):
                    self.assert_admitted("rollout.jsonl", self.code_mode(out=out, cmd=cmd, stdout=stdout), "session",
                                         [3, 4])

    def test_codex_escaped_copy_is_one_exact_literal(self):
        stdout = self.stdout("cat")
        lit = json.dumps(stdout, ensure_ascii=False)
        cases = {"double-escaped": '{"r":' + json.dumps(json.dumps(stdout)) + "}",
                 "a literal of a changed output": _sol(stdout.replace("line after", "LINE AFTER")),
                 "an escaped quote before the literal": '{"r":"x\\' + lit + '"}'}
        for case, out in cases.items():
            with self.subTest(case):
                self.assert_split("rollout.jsonl", self.code_mode(out=out), "session", [3], [4])
        # round 6 (B17-22: one literal per read): the read's own literal once, beside a changed one holding the line
        changed = json.dumps(stdout.replace("line after", "LINE AFTER"), ensure_ascii=False)
        both = self.code_mode(out='{"a":' + lit + ',"b":' + changed + "}")
        self.assert_split("rollout.jsonl", both, "session", [3], [4])
        with _mutant("_copy_hits", ("s[p:p + len(e)] == e", "True")):
            self.assert_split("rollout.jsonl", both, "session", [3, 4], [])
        red("B17 round 5 the escaped span is one exact literal")

    def test_codex_lossy_copy_refuses(self):
        stdout = self.stdout("cat")
        middle = "line before\n... [12 bytes truncated] ...\n" + self.text + "\n"
        self.assert_split("rollout.jsonl", self.code_mode(out=_sol(middle)), "session", [3], [4])

    # ---- B17-18: positions, not matches (the reviewer's D1 to D4b)
    def test_codex_positions_count_once(self):
        cat, grep = SHELL_READS[0][1], SHELL_READS[2][1]
        co, go = self.stdout("cat"), self.stdout("grep")
        cases = {
            "D1 the doc read twice, two exec pairs": (self.pair("a", 1, [(cat, co)], co) + self.pair("b", 4, [(cat, co)], co),
                                                     [3, 4, 6, 7], []),
            "D2 a grep then a cat, two exec pairs": (self.pair("a", 1, [(grep, go)], go) + self.pair("b", 4, [(cat, co)], co),
                                                    [3, 4, 6, 7], []),
            "D3 two cat reads, the line again outside the copy": (self.pair("a", 1, [(cat, co), (cat, co)],
                                                                            co + "zz" + self.text), [3, 4], [5]),
            "D4 a grep and a cat read, the line again after": (self.pair("a", 1, [(grep, go), (cat, co)],
                                                                         co + "tail:" + self.text), [3, 4], [5]),
        }
        for case, (recs, ruled, refused) in cases.items():
            with self.subTest(case):
                self.assert_split("rollout.jsonl", _cc(_cx_meta(), *recs), "session", ruled, refused)
        d4b = _cc(_cx_meta(), _cx_custom(1, "a"), _cx_end(2, "a-0", ["/bin/bash", "-lc", grep], go),
                  _cx_end(3, "a-1", ["/bin/bash", "-lc", cat], co),
                  _cx_line(4, "response_item", {"type": "custom_tool_call_output", "call_id": "a", "id": "x",
                                                "output": [{"type": "input_text", "text": co},
                                                           {"type": "input_text", "text": "q" + self.text}]}))
        self.assert_split("rollout.jsonl", d4b, "session", [3, 4], [5])

    def test_codex_one_position_matched_by_two_sources_counts_once(self):
        cat, co = SHELL_READS[0][1], self.stdout("cat")
        body = _cc(_cx_meta(), *self.pair("a", 1, [(cat, co), (cat, co)], co))
        self.assert_admitted("rollout.jsonl", body, "session", [3, 4, 5])
        with _mutant("_copy_hits", ("if q not in seen:", "if True:")):
            self.assert_split("rollout.jsonl", body, "session", [3, 4], [5])
        red("B17 round 5 a position counts once")

    def test_codex_two_positions_count_twice(self):
        script = SHELL_READS[0][1]                 # B24-2 item 5: cat of the doc once (cat labels nothing)
        co = self.stdout("cat") * 2
        body = _cc(_cx_meta(), *self.pair("a", 1, [(script, co)], co))
        self.assert_admitted("rollout.jsonl", body, "session", [3, 4])
        with _mutant("_copy_hits", ("return hits", "return hits[:1]")):
            self.assert_split("rollout.jsonl", body, "session", [3], [4])
        red("B17 round 5 every position counts")

    # ---- B17-19: an exec output's sources lie inside its own exec pair
    def test_codex_exec_output_reads_only_its_own_pair(self):
        grep, go = SHELL_READS[2][1], self.stdout("grep")
        body = _cc(_cx_meta(), *self.pair("a", 1, [(SHELL_READS[0][1], "ok\n")], "ok\n"),
                   _cx_custom(4, "b", inp="text('x')"), _cx_custom_out(5, "b", go),
                   _cx_end(6, "c-0", ["/bin/bash", "-lc", grep], go))
        # od57-line: the exec output outside its pair is a shell output copy, so its whole line is admitted; a byte
        # after the pinned bytes refuses both; the window's witness holds on the read rules alone (retargeted)
        self.assert_split("rollout.jsonl", body, "session", [6, 7], [])
        self.assert_split("rollout.jsonl", self.line_twin(body), "session", [], [6, 7])
        with self.reads_only():
            self.assert_split("rollout.jsonl", body, "session", [7], [6])
            # round 6 (B17-21): a read outside every window is no source either, so the witness drops both window
            # checks
            with _mutant("_shape_strings", ("cl[0] < ln < line", "True")), \
                    _mutant("_shape_calls", ("sum(1 for c, o in windows if c < n < o) == 1", "True")):
                self.assert_split("rollout.jsonl", body, "session", [6, 7], [])
        red("B17 round 5 the exec pair's window")

    # ---- NIT 2: the event's payload type, the file kind, a response's own entry
    def test_codex_command_execution_of_another_event_refuses(self):
        item = {"type": "CommandExecution", "id": "e1", "command": ["/bin/bash", "-lc", SHELL_READS[0][1]],
                "aggregated_output": self.stdout("cat")}
        body = _cc(_cx_meta(), _cx_line(1, "event_msg", {"type": "agent_message", "item": item}))
        wide = _widened(CODEX_SHAPES, CX_ITEM, "call", at=_plus(CODEX_SHAPES[CX_ITEM]["call"], ("payload", "item"),
                                                                 type=["event_msg"]))
        self.data_witness("NIT 2 the event's payload type", "rollout.jsonl", body, "session", [2], wide)

    def test_codex_rollout_line_in_a_stream_file_refuses(self):
        body = _cc({"type": "thread.started", "thread_id": "thread-1"},
                   _cx_end(1, "e1", ["/bin/bash", "-lc", SHELL_READS[0][1]], self.stdout("cat")))
        wide = _widened(CODEX_SHAPES, CX_ITEM, None, kinds=("session", "stream"))
        self.data_witness("NIT 2 the file kind", "turn-1.jsonl", body, "stream", [2], wide)

    def test_gemini_response_answers_its_own_entry(self):
        grep_entry = _gem_call("call-g2", "grep_search", {"pattern": "pinned"}, "No matches")
        grep_entry["result"] = [_gem_response("call-g1", "run_shell_command",
                                              _gem_shell(self.stdout("cat").rstrip("\n")))]
        body = _cc(GEM_HEAD, _gem_message("msg-g1", [self.shell_call(), grep_entry]))
        at = tuple((p, r, None) for p, r, _ in GEM_SHAPES[GEM_RESPONSE]["result"]["at"])
        wide = _widened(GEM_SHAPES, GEM_RESPONSE, "result", at=at)
        self.data_witness("NIT 2 a response's own entry", "session.jsonl", body, "session", [2], wide)

    # ---- NIT 5: the rollout CommandExecution's argv is a list
    def test_codex_command_execution_argv_string_refuses(self):
        item = {"type": "CommandExecution", "id": "e1", "command": _cx_wrap(SHELL_READS[0][1]),
                "aggregated_output": self.stdout("cat")}
        body = _cc(_cx_meta(), _cx_line(1, "event_msg", {"type": "item_completed", "item": item}))
        # od57-line: the shell tool's whole output line is admitted whatever the argv's form (retargeted)
        wide = _with_tool(CODEX_SHAPES, CX_ITEM, "shell", kind="wrapped")
        self.data_witness("NIT 5 the argv's list form", "rollout.jsonl", body, "session", [2], wide, line=True)

    # ---- NIT 3: the schema's copy_of and wrapped-tool cases
    def test_the_copy_and_wrapped_schema_refuses(self):
        p = self.write("plain.jsonl", _cc({"type": "assistant", "text": "nothing ruled"}))
        cx, gm = list(CODEX_SHAPES), list(GEM_SHAPES)
        wrap = cx[CX_STREAM]["tools"]["shell"]
        bad = {
            "copy_of names a non-joined shape": cx[:CX_COPY] + [dict(cx[CX_COPY], copy_of=3), gm[GEM_STREAM]],
            "copy_of names itself": cx[:CX_COPY] + [dict(cx[CX_COPY], copy_of=CX_COPY)],
            "copy_of out of range": cx[:CX_COPY] + [dict(cx[CX_COPY], copy_of=9)],
            "a copy tool with copy_of None": cx[:CX_COPY] + [dict(cx[CX_COPY], copy_of=None)],
            "copy_of on a shape without copy tools": [dict(cx[CX_STREAM], copy_of=CX_ITEM)] + cx[1:],
            "copy_of names a copy shape": [cx[0], cx[1], dict(cx[CX_COPY], copy_of=1),
                                           dict(cx[CX_COPY], copy_of=2)],
            "a wrapped tool without shells": [dict(cx[CX_STREAM], tools={"shell": dict(wrap, shells=None)})],
            "a wrapped tool without flags": [dict(cx[CX_STREAM], tools={"shell": dict(wrap, flags=None)})],
            "a wrapped tool with a relative shell": [dict(cx[CX_STREAM], tools={"shell": dict(wrap,
                                                                                              shells=("bash",))})],
            "shells on a script tool": [dict(gm[GEM_STREAM], tools={"run_shell_command": dict(
                gm[GEM_STREAM]["tools"]["run_shell_command"], shells=("/bin/bash",))})],
            "no file kind": [dict(gm[GEM_STREAM], kinds=())],
            "an unknown file kind": [dict(gm[GEM_STREAM], kinds=("ledger",))],
            "an anchor past its path": [dict(gm[GEM_STREAM], call=dict(gm[GEM_STREAM]["call"],
                                                                        at=(((), {}, 3),)))],
        }
        for case, shapes in bad.items():
            with self.subTest(case):
                with self.assertRaises(sr.ScanError):
                    sr.scan([(p, "transcript")], SECRETS, rules_scanner=no_findings, read_shapes=tuple(shapes))
        red("B17 round 5 the copy_of and wrapped schema")


for _cls_from in (TestOD57OtherArms, TestB17ReadShapes, TestB17Round3, TestB17Round4):
    for _name in [n for n in vars(_cls_from) if n.startswith("test_")]:
        setattr(TestB17Round5, _name, None)  # each earlier class's tests run once, in their own class


# ------------------------------------------------------------------------------------------------- B17, round 6
# glitch-26's rulings B17-20 to B17-22 on review REVIEW-vendor-b17-8776055a (19 Oct 2026): gpt-6.1-sol's literal keeps
# non-ASCII raw, as JSON.stringify does and the doc needs (17 non-ASCII characters), and only that form is admitted; the
# literal is exactly one per read and a JSON string value (after `:`, `[` or `,`); a CommandExecution counts only when it
# lies in exactly one exec window, and an exec call with more than one output admits nothing.
NON_ASCII = "versión — αβγ ✓"


class TestB17Round6(TestB17Round5):
    """Round 6: the non-ASCII literal, the literal's tokenization, and one window per read, each with a witness."""

    def literal(self, stdout, ensure_ascii=False):
        return json.dumps(stdout, ensure_ascii=ensure_ascii)

    # ---- B17-20: the non-ASCII literal kept raw
    def test_codex_sol_non_ascii_literal_is_admitted(self):
        stdout = f"line before {NON_ASCII}\n{self.text}\nline after {NON_ASCII}\n"
        body = self.code_mode(out=_sol(stdout), stdout=stdout)
        self.assert_admitted("rollout.jsonl", body, "session", [3, 4])
        with _mutant("_copy_hits", ("json.dumps(a, ensure_ascii=False)", "json.dumps(a, ensure_ascii=True)"),
                     ("json.dumps(a[:k], ensure_ascii=False)", "json.dumps(a[:k], ensure_ascii=True)")):
            self.assert_split("rollout.jsonl", body, "session", [3], [4])
        red("B17 round 6 the literal keeps non-ASCII raw")

    def test_codex_ascii_escaped_literal_refuses(self):
        stdout = f"line before {NON_ASCII}\n{self.text}\nline after\n"
        out = '{"exit_code":0,"output":' + self.literal(stdout, ensure_ascii=True) + "}"
        self.assert_split("rollout.jsonl", self.code_mode(out=out, stdout=stdout), "session", [3], [4])

    # ---- B17-22: one literal per read, at a JSON value position
    def test_codex_literal_is_one_json_value(self):
        stdout = self.stdout("cat")
        lit = self.literal(stdout)
        admitted = {"after a colon and a space": '{"output": ' + lit + "}",
                    "in an array": "[" + lit + "]", "after a comma": '[1, ' + lit + "]"}
        for case, out in admitted.items():
            with self.subTest(admitted=case):
                self.assert_admitted("rollout.jsonl", self.code_mode(out=out), "session", [3, 4])
        refused = {"two literals of the read": '{"a":' + lit + ',"b":' + lit + "}",
                   "after a previous string's closing quote": '"zz' + lit + "}",
                   "after text": "output=" + lit}
        for case, out in refused.items():
            with self.subTest(refused=case):
                self.assert_split("rollout.jsonl", self.code_mode(out=out), "session", [3], [4])
        with _mutant("_copy_hits", ("_json_value_at(s, p)", "True")):
            self.assert_split("rollout.jsonl", self.code_mode(out=refused["after text"]), "session", [3, 4], [])
        red("B17 round 6 the literal is a JSON value")
        with _mutant("_copy_hits", ("s.count(e) == 1", "True")):
            self.assert_split("rollout.jsonl", self.code_mode(out=refused["two literals of the read"]), "session",
                              [3, 4], [])
        red("B17 round 6 one literal per read")

    # ---- B17-21: one window per read, one output per call
    def test_codex_read_in_two_windows_refuses(self):
        cat, co = SHELL_READS[0][1], self.stdout("cat")
        body = _cc(_cx_meta(), _cx_custom(1, "a", inp="text('x')"), _cx_custom(2, "b"),
                   _cx_end(3, "b-0", ["/bin/bash", "-lc", cat], co), _cx_custom_out(4, "b", co),
                   _cx_custom_out(5, "a", co))
        # od57-line: both outputs are shell output copies, so their whole lines are admitted; a byte after the pinned
        # bytes refuses all three; the window's witness holds on the read rules alone (retargeted)
        self.assert_split("rollout.jsonl", body, "session", [4, 5, 6], [])
        self.assert_split("rollout.jsonl", self.line_twin(body), "session", [], [4, 5, 6])
        with self.reads_only():
            self.assert_split("rollout.jsonl", body, "session", [4], [5, 6])
            with _mutant("_shape_calls", ("sum(1 for c, o in windows if c < n < o) == 1", "True")):
                self.assert_split("rollout.jsonl", body, "session", [4, 5, 6], [])
        red("B17 round 6 one window per read")

    def test_codex_call_with_two_outputs_refuses(self):
        cat, co = SHELL_READS[0][1], self.stdout("cat")
        body = _cc(_cx_meta(), _cx_custom(1, "a"), _cx_end(2, "a-0", ["/bin/bash", "-lc", cat], co),
                   _cx_custom_out(3, "a", co), _cx_custom_out(4, "a", co))
        # od57-line: both outputs are shell output copies, so their whole lines are admitted; a byte after the pinned
        # bytes refuses all three; the one-output witness holds on the read rules alone (retargeted)
        self.assert_split("rollout.jsonl", body, "session", [3, 4, 5], [])
        self.assert_split("rollout.jsonl", self.line_twin(body), "session", [], [3, 4, 5])
        with self.reads_only():
            self.assert_split("rollout.jsonl", body, "session", [3], [4, 5])
            with _mutant("_shape_strings", ("len(out_lines.get(node[spec[\"id\"]]) or ()) != 1", "False")), \
                    _mutant("_shape_calls", ("len(out_lines[c]) == 1", "True")):
                self.assert_split("rollout.jsonl", body, "session", [3, 4, 5], [])
        red("B17 round 6 one output per call")


for _cls_from in (TestOD57OtherArms, TestB17ReadShapes, TestB17Round3, TestB17Round4, TestB17Round5):
    for _name in [n for n in vars(_cls_from) if n.startswith("test_")]:
        setattr(TestB17Round6, _name, None)  # each earlier class's tests run once, in their own class


# ------------------------------------------------------------------------------------------------- B20-5
# glitch-26's ruling B20-5 (lane vendor-b20, Tue 20 Oct 2026; Gemini practice walk w-g11 held at the drive scan): OD57's
# line, by its content sha256, is admitted when a git diff carries it: exactly one leading "+", "-" or " " before the
# 80 bytes, in a `git log -p` or `git show` read run in the take's own folder, in Gemini and Codex read output alike,
# through the read shapes' shared path. Nothing else widens: another line, a doubled prefix, another git subcommand or
# option, a partial match, another file's hunk, another directory, or the Claude path. w-g11's shape (from the
# investigator's notes; no walk record read, the value never copied: the line is the doc's own, as OD57's tests take it):
# run_shell_command {command: "git log -p -n 1 7bd5b8b"}, its stream tool_result `output` and its session toolCalls
# entry's resultDisplay holding the line once with a "+" prefix under the doc's diff header; the functionResponse output
# truncated short of it.
GIT_CMD = "git log -p -n 1 7bd5b8b"
GIT_SHA = "7bd5b8b" + "0" * 33
DOC_PATH = "gars/" + DOC_REL


def _git_out(text, prefix="+", doc=DOC_PATH, header=None, before=(), between=()):
    """A `git log -p` of one commit: its header and message, then the diff of `doc` with one hunk holding
    `prefix + text` (`header` replaces the diff header line; `between` lines sit between the hunk header and it)."""
    return "\n".join([f"commit {GIT_SHA}", "Author: Agent <agent@example.invalid>",
                      "Date:   Mon Oct 19 00:00:00 2026 +0000", "", "    record the pinned versions", "", *before,
                      header or f"diff --git a/{doc} b/{doc}", "index 1111111..2222222 100644", f"--- a/{doc}",
                      f"+++ b/{doc}", "@@ -172,6 +172,6 @@ heading", " line before", *between, "-an older line",
                      prefix + text, " line after", ""])


# B20-6 and B20-7 (glitch-26, round 4, on review 21fc1c7e): arm O's git read binds its folder (the rollout
# CommandExecution's cwd is exactly file:// + session_meta's cwd, as the committed rollouts write them: w-o14's
# session_meta cwd '/tmp/run-b6ddc761', its CommandExecutions' 'file:///tmp/run-b6ddc761'; protocol/src/protocol.rs:3171
# SessionMeta.cwd a PathBuf, protocol/src/items.rs:265 CommandExecutionItem.cwd a PathUri serialized as its URL,
# utils/path-uri/src/lib.rs:689-695); the header names the doc's own repo path exactly; the two ruled forms only.
GIT_FORMS = (GIT_CMD, "git show 7bd5b8b")
GIT_REFUSED = ("git diff", "git blame gars/_references/environment.md", "git log -n 1 7bd5b8b", "git log -p",
               "git log --patch -3 --no-color", "git show --max-count=1 HEAD", "git log -p HEAD~1..HEAD", "git show -0",
               "git log -p origin/main", "git show 7bd5b8b gars/_references/environment.md", "git log -p -n 2 7bd5b8b",
               "git log -p -1 7bd5b8b", "git show HEAD", "git show 7bd5b8", "git show 7BD5B8B", "git show " + "a" * 41,
               "git -C /elsewhere log -p", "git log -p --output=/tmp/x", "git log -p --ext-diff",
               "git log -p -n 1 7bd5b8b | head", "cd /elsewhere && git log -p", "GIT_DIR=/x git log -p",
               "git show HEAD:gars/_references/environment.md", "git log  -p -n 1 7bd5b8b", "git log -p -n x 7bd5b8b",
               "git cat-file -p 7bd5b8b", "git grep -n Key", "/usr/bin/git log -p -n 1 7bd5b8b",
               "git log -p -n 1 7bd5b8b\nid", "git show 7bd5b8b ", "git log -p -n 1 7bd5b8b --ext-diff")
CX_META_CWD = "/run/gars"
CX_CWD = "file://" + CX_META_CWD


class TestB20GitReads(TestB17Round6):
    """B20-5 to B20-7: the git read and its diff prefix, admitted on the read shapes that bind the read's folder (the
    Gemini shapes by their arguments, the Codex rollout's CommandExecution by its cwd); each guard with a witness that
    goes red alone."""

    def b20_witness(self, label, name, body, kind, lines, fn, *edits):
        """Refused as is, on `lines`; admitted on exactly those lines with only `edits` made to sr.<fn>."""
        self.assert_refused(name, body, kind, lines)
        with _mutant(fn, *edits):
            self.assert_admitted(name, body, kind, lines)
        red(f"B20 {label}")

    def gem_stream(self, out, command=GIT_CMD, params=None):
        return _cc({"type": "init", "timestamp": TS, "session_id": "session-1", "model": "model-under-test"},
                   _gem_use("call-g1", "run_shell_command", params or {"command": command, "description": "show it"}),
                   _gem_result("call-g1", out))

    def gem_session(self, out, command=GIT_CMD, args=None, name="run_shell_command"):
        """w-g11's session record: the entry's resultDisplay holds the git output; its functionResponse output is
        truncated short of the line."""
        call = _gem_call("call-g1", name, args or {"command": command}, _gem_shell("commit " + GIT_SHA + "\n[truncated]"),
                         out)
        return _cc(GEM_HEAD, GEM_USER, _gem_message("msg-g1", [call]))

    def cx_stream(self, out, command=GIT_CMD):
        return _cc({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
                   _cx_item("item.started", "item_1", _cx_wrap(command), "", "in_progress"),
                   _cx_item("item.completed", "item_1", _cx_wrap(command), out))

    def cx_rollout(self, out, cmd=GIT_CMD, cwd=CX_CWD, metas=(CX_META_CWD,), copy=None):
        """arm O's rollout as the committed ones are: session_meta {cwd: the run tree}, the exec call, its script's
        CommandExecution {cwd: file:// + the run tree} (lines 2 and 3 after the metas), the exec's output (verbatim, or
        `copy`)."""
        recs = [_cx_line(0, "session_meta", {"id": "thread-1", "cli_version": "0.162.1", "history_mode": "paginated",
                                              "cwd": m}) for m in metas]
        recs.append(_cx_custom(len(recs), "call-o1"))
        ce = _cx_end(len(recs), "exec-cmd-1", ["/bin/bash", "-lc", cmd], out)
        ce["payload"]["item"]["cwd"] = cwd
        recs.append(ce)
        recs.append(_cx_custom_out(len(recs), "call-o1", f"Script completed\n{out}exit code 0" if copy is None else copy))
        return _cc(*recs)

    def cx_lines(self, metas=1):
        return [metas + 2, metas + 3]

    # ---- admitted: w-g11's shape on Gemini, and the same read in arm O's rollout, each prefix, the two ruled forms
    def test_gemini_wg11_git_log_is_admitted(self):
        self.assert_admitted("turn-1.jsonl", self.gem_stream(_git_out(self.text)), "stream", [3])
        self.assert_admitted("native-turn-1.jsonl", self.gem_session(_git_out(self.text)), "session", [3])
        for prefix in ("+", "-", " "):
            for cmd in GIT_FORMS:
                with self.subTest(prefix=prefix, cmd=cmd):
                    self.assert_admitted("turn-1.jsonl", self.gem_stream(_git_out(self.text, prefix), cmd), "stream",
                                         [3])
        self.assert_admitted("turn-1.jsonl", self.gem_stream(_git_out(self.text), params={"command": GIT_CMD}),
                             "stream", [3])

    def test_codex_git_reads_are_admitted(self):
        out = _git_out(self.text)
        for cmd in GIT_FORMS:
            with self.subTest(cmd=cmd):
                self.assert_admitted("rollout.jsonl", self.cx_rollout(out, cmd), "session", self.cx_lines())
        self.assert_admitted("rollout.jsonl", self.cx_rollout(out, copy=_sol(out)), "session", self.cx_lines())

    # ---- refused: nothing else widens (B20-5, B20-7)
    def test_gemini_git_near_misses_refuse(self):
        t = self.text
        outs = {
            "another line": _git_out(_one_char_off(t)),
            "a doubled prefix": _git_out(t, "++"),
            "a plus and a space": _git_out(t, "+ "),
            "no prefix": _git_out(t, ""),
            "a tab prefix": _git_out(t, "\t"),
            "a partial match": _git_out(t + " x"),
            "a cut line": _git_out(t[:-1]),
            "another file's hunk": _git_out(t, doc="gars/_references/other.md"),
            "another folder's doc (B20-7)": _git_out(t, doc="evil/_references/environment.md"),
            "the doc's path cut (B20-7)": _git_out(t, doc=DOC_REL),
            "a renamed side": _git_out(t, header=f"diff --git a/gars/other.md b/{DOC_PATH}"),
            "no diff header": "\n".join(["@@ -1,1 +1,1 @@", "+" + t, ""]),
            "outside a hunk body": _git_out(t, between=(f"commit {GIT_SHA}",)),
        }
        for case, out in outs.items():
            with self.subTest(case=case):
                if case == "no prefix":          # od57-line: a whole bare line of the shell's output (retargeted)
                    self.assert_line_retargeted("turn-1.jsonl", self.gem_stream(out), "stream", [3])
                else:
                    self.assert_refused("turn-1.jsonl", self.gem_stream(out), "stream", [3])
        for cmd in GIT_REFUSED:
            with self.subTest(cmd=cmd):
                self.assert_refused("turn-1.jsonl", self.gem_stream(_git_out(self.text), cmd), "stream", [3])

    def test_gemini_no_route_reaches_another_folder(self):
        """B20-6: a Gemini git read carries no folder but its arguments: any argument but command and description
        (dir_path, is_background, an unknown key) refuses, on every Gemini shape; the command's own folder switches
        refuse."""
        out = _git_out(self.text)
        for extra in ({"dir_path": "/elsewhere"}, {"dir_path": "."}, {"is_background": False}, {"cwd": "/elsewhere"}):
            with self.subTest(extra=extra):
                args = dict({"command": GIT_CMD, "description": "show it"}, **extra)
                self.assert_refused("turn-1.jsonl", self.gem_stream(out, params=args), "stream", [3])
                self.assert_refused("native-turn-1.jsonl", self.gem_session(out, args=args), "session", [3])
                rec = {"id": "msg-u2", "timestamp": TS, "type": "user",
                       "content": [_gem_response("call-g1", "run_shell_command", _gem_shell(out))]}
                call = _gem_call("call-g1", "run_shell_command", args, _gem_shell(out), "")
                self.assert_refused("native-turn-1.jsonl", _cc(GEM_HEAD, GEM_USER, _gem_message("msg-g1", [call]), rec),
                                    "session", [3, 4])
        for cmd in ("git -C /elsewhere log -p -n 1 7bd5b8b", "git --git-dir=/x/.git show 7bd5b8b",
                    "git --work-tree=/x show 7bd5b8b", "cd /elsewhere && git show 7bd5b8b",
                    "GIT_DIR=/x/.git git show 7bd5b8b", "env GIT_DIR=/x/.git git show 7bd5b8b"):
            with self.subTest(cmd=cmd):
                self.assert_refused("turn-1.jsonl", self.gem_stream(out, cmd), "stream", [3])

    def test_codex_git_reads_need_the_bound_folder(self):
        """B20-6: arm O's git read is admitted only in the rollout, its CommandExecution's cwd exactly file:// + the
        run tree its session_meta names; the stream (no cwd) admits no git read."""
        t = self.text
        out = _git_out(t)
        self.assert_refused("turn-1.jsonl", self.cx_stream(out), "stream", [4])
        cases = {
            "another repo": dict(cwd="file:///tmp/other-repo"),
            "a folder inside the run tree": dict(cwd=CX_CWD + "/gars"),
            "the plain path": dict(cwd=CX_META_CWD),
            "a trailing slash": dict(cwd=CX_CWD + "/"),
            "no session_meta": dict(metas=()),
            "two session_meta": dict(metas=(CX_META_CWD, CX_META_CWD)),
            "a relative session_meta cwd": dict(cwd="file://run/gars", metas=("run/gars",)),
        }
        for case, kw in cases.items():
            with self.subTest(case=case):
                body = self.cx_rollout(out, **kw)
                self.assert_refused("rollout.jsonl", body, "session", self.cx_lines(len(kw.get("metas", (1,)))))
        self.assert_split("rollout.jsonl", self.cx_rollout(_git_out(t, "++")), "session", [], self.cx_lines())
        self.assert_split("rollout.jsonl", self.cx_rollout(out, "git diff 7bd5b8b"), "session", [], self.cx_lines())
        # the cat read of B17 keeps its own road: no cwd is asked of it
        cat = self.stdout("cat")
        self.assert_admitted("rollout.jsonl", self.cx_rollout(cat, SHELL_READS[0][1], cwd="file:///tmp/other-repo"),
                             "session", self.cx_lines())

    def test_claude_git_read_refuses(self):
        """The Claude path is not widened: a Bash git log -p of the doc's diff stays refused."""
        p = self.write("transcript.jsonl", self.bash_record(GIT_CMD, _git_out(self.text)))
        r, _ = self.scan([(p, "transcript")])
        self.assertEqual(r["ruled"], [])
        self.assertNotEqual(r["refused"], [])

    def test_gemini_a_cat_read_takes_no_diff_prefix(self):
        """A cat of the doc whose output holds a diff-shaped hunk: the prefix is a git read's only."""
        self.assert_refused("turn-1.jsonl", self.gem_stream(_git_out(self.text), SHELL_READS[0][1]), "stream", [3])

    def test_a_git_binding_off_its_schema_refuses(self):
        bad = ({"args": "command"}, {"args": ()}, {"cwd": "cwd", "prefix": "file://"}, {"cwd": "", "prefix": "x",
               "meta": ({"type": ("session_meta",)}, "payload.cwd")}, {"args": ("command",), "cwd": "cwd"}, "args")
        for git in bad:
            with self.subTest(git=git):
                shapes = (dict(GEM_SHAPES[0], git=git),)
                with self.assertRaises(sr.ScanError):
                    sr.scan([(self.write("turn-1.jsonl", b"{}\n"), "stream")], SECRETS,
                            rules_scanner=_Gitleaks(self.text[:40]), read_shapes=shapes)
        with _mutant("_shape_ok", ("_git_ok(shape)", "True")):
            sr.scan([(self.write("turn-1.jsonl", b"{}\n"), "stream")], SECRETS, rules_scanner=_Gitleaks(self.text[:40]),
                    read_shapes=(dict(GEM_SHAPES[0], git="args"),))
        red("B20 the git binding's schema")

    def test_the_arms_bind_their_git_reads(self):
        """B20-6: every Gemini shape binds by arguments (command and description only); arm O's rollout
        CommandExecution binds by its cwd to session_meta's; the stream and the copy shape bind nothing."""
        for s in GEM_SHAPES:
            if s["shape"] == "session grep display":       # B24: a display of grep_search, no shell, no git read
                self.assertNotIn("git", s)
                continue
            self.assertEqual(s.get("git"), {"args": ("command", "description")}, s["shape"])
        got = {s["shape"]: s.get("git") for s in CODEX_SHAPES}
        self.assertEqual(got, {"stream command_execution": None, "rollout exec output": None,
                               "rollout CommandExecution": {"cwd": "cwd", "prefix": "file://",
                                                            "meta": ({"type": ("session_meta",)}, "payload.cwd")}})

    # ---- one witness per guard, each red alone
    def test_gemini_witnesses_the_command(self):
        for label, cmd, edit in (
                ("the log form", "git log -p -n 9 7bd5b8b",
                 ('t[:5] == ["git", "log", "-p", "-n", "1"]', 't[:2] == ["git", "log"]')),
                ("the show form", "git diff 7bd5b8b", ('t[:2] == ["git", "show"]', 't[0] == "git"')),
                ("the commit", "git show HEAD~1..HEAD", ("_GIT_COMMIT.fullmatch(c) is not None", "True")),
                ("the show length", "git show 7bd5b8b gars/x", ("len(t) == 3 and", "len(t) >= 3 and")),
                ("the log length", "git log -p -n 1 7bd5b8b --ext-diff", ("len(t) == 6 and", "len(t) >= 6 and"))):
            with self.subTest(label):
                self.b20_witness(label, "turn-1.jsonl", self.gem_stream(_git_out(self.text), cmd), "stream", [3],
                                 "_ruled_git", edit)

    def test_gemini_witness_the_arguments(self):
        self.b20_witness("the argument allow-list", "native-turn-1.jsonl",
                         self.gem_session(_git_out(self.text), args={"command": GIT_CMD, "dir_path": "/elsewhere"}),
                         "session", [3], "_reads_git", ('set(args) <= set(git["args"])', "True"))

    def test_gemini_witness_a_git_read_is_a_shell_read(self):
        call = _gem_call("call-g1", "read_file", {"command": GIT_CMD}, _git_out(self.text))
        shapes = (dict(GEM_SHAPES[1], tools=dict(GEM_SHAPES[1]["tools"], read_file=dict(GEM_SHAPES[1]["tools"][
            "read_file"], arg="command"))),)
        self.shapes_override = shapes
        try:
            self.b20_witness("a shell read only", "native-turn-1.jsonl",
                             _cc(GEM_HEAD, GEM_USER, _gem_message("msg-g1", [call])), "session", [3], "_reads_git",
                             ('tool["kind"] == "script" and _ruled_git(arg)', "_ruled_git(arg)"))
        finally:
            self.shapes_override = None

    def test_codex_witnesses_the_folder(self):
        out = _git_out(self.text)
        for label, kw, fn, edit in (
                ("the bound folder", dict(cwd="file:///tmp/other-repo"), "_reads_git", ("bound is not True", "False")),
                ("one session_meta", dict(metas=(CX_META_CWD, "/tmp/other")), "_git_meta",
                 ("len(metas) == 1", "len(metas) >= 1")),
                ("an absolute run tree", dict(cwd="file://run/gars", metas=("run/gars",)), "_git_meta",
                 ('metas[0].startswith("/")', "True")),
                ("the folder's file:// form", dict(cwd=CX_META_CWD), "_git_bound",
                 ('== git["prefix"] + meta', 'in (git["prefix"] + meta, meta)'))):
            with self.subTest(label):
                lines = self.cx_lines(len(kw.get("metas", (1,))))
                self.b20_witness(label, "rollout.jsonl", self.cx_rollout(out, **kw), "session", lines, fn, edit)
        with self.subTest("the stream binds no folder"):
            self.b20_witness("the stream binds no folder", "turn-1.jsonl", self.cx_stream(out), "stream", [4],
                             "_reads_git", ("bound is not True", "False"))

    def test_gemini_witnesses_the_diff(self):
        t = self.text
        for label, out, fn, edit in (
                ("one prefix", _git_out(t, "++"), "_ruled_diff_line",
                 ('ln[1:].encode("utf-8", "surrogateescape")', 'ln.lstrip("+- ").encode("utf-8", "surrogateescape")')),
                ("a hunk body", _git_out(t, between=(f"commit {GIT_SHA}",)), "_ruled_diff_line",
                 ('lines[j][:1] not in _DIFF_PREFIXES + ("\\\\",)', "False")),
                ("a diff header", "\n".join(["@@ -1,1 +1,1 @@", "+" + t, f"diff --git a/{DOC_PATH} b/{DOC_PATH}"]),
                 "_ruled_diff_line", ("if k < 0:", "if False:")),
                ("the doc's diff", _git_out(t, doc="gars/_references/other.md"), "_ruled_diff_line",
                 ("_git_doc_header(lines[k])", "True")),
                ("the doc's own path", _git_out(t, doc="evil/_references/environment.md"), "_git_doc_header",
                 ("m[2] == _RULED_GIT_PATH", "m[2].endswith(_RULED_DOC)")),
                ("one path both sides", _git_out(t, header=f"diff --git a/gars/other.md b/{DOC_PATH}"),
                 "_git_doc_header", ("m[1] == m[2] and", ""))):
            with self.subTest(label):
                self.b20_witness(label, "turn-1.jsonl", self.gem_stream(out), "stream", [3], fn, edit)

    def test_gemini_witness_the_prefix_is_a_git_reads(self):
        self.b20_witness("only a git read", "turn-1.jsonl", self.gem_stream(_git_out(self.text), SHELL_READS[0][1]),
                         "stream", [3], "_line_text", ('tool.get("git")', "True"))

    def test_codex_witness_the_copy_keeps_the_git_read(self):
        """A behaviour test: with the copy rule blind to a git source, the exec output's copy is lost."""
        body = self.cx_rollout(_git_out(self.text))
        self.assert_split("rollout.jsonl", body, "session", [3, 4], [])
        with _mutant("_copy_hits", ("f = _line_text(lines_a, i, tool, ruling, None)",
                                    'f = None if tool.get("git") else _line_text(lines_a, i, tool, ruling, None)')):
            self.assert_split("rollout.jsonl", body, "session", [3], [4])
        red("B20 the copy reads a git source as a diff")

    def test_codex_witness_the_wrapped_git_read(self):
        self.b20_witness("the wrapped script", "rollout.jsonl", self.cx_rollout(_git_out(self.text), "git diff 7bd5b8b"),
                         "session", [3, 4], "_ruled_git", ('t[:2] == ["git", "show"]', 't[0] == "git"'))


class TestOD57Gap(TestOD57Chain):
    """od57-gap (STOP2-OD57-GAP-20261107): a compound shell read admits only a labelled line of its labelled reads (grep,
    or rg with typed file operands), the label one of that read's typed operands. The two stop shapes carry the closed
    features of the counted run's s-0e780d and s-3c4f8d (synthetic commands; the takes' own words were never read);
    the widened shapes (rg, sed -n, awk, echo) are the open shell reads STOP2-OD57-GAP-20261107 section 4 lists."""

    DOC = "_references/environment.md"
    OTHER = "_references/gars-bio.lock.txt"

    def labelled(self, n=False, text=None, label=None):
        return f"{label or self.DOC}:{'175:' if n else ''}{self.text if text is None else text}\n"

    def both_kinds(self, cmd, out):
        for kind, side in (("transcript", False), ("stream", True)):
            with self.subTest(cmd=cmd, kind=kind):
                self.assertFalse(sr._ruled_bash(cmd))            # the frozen allow-list still refuses it whole
                self.assertTrue(self.admitted(self.bash_record(cmd, out, side), kind))

    def test_the_two_stop_shapes_are_admitted(self):
        doc = self.DOC
        # s-0e780d's features: no cd, grep (2 operands) ; grep (3 operands, the doc among them) | head; no -n
        self.both_kinds("grep -i pinned " + doc + " _references/gars-bio.conda.txt; grep -i pinned README.md " + doc
                        + " docs/setup.md | head -20", self.labelled())
        # s-3c4f8d's features: cd &&, grep -n (2 operands) | head ; head <file> | cut
        self.both_kinds("cd /tmp/run-c8021046/gars && grep -n Key " + doc + " " + self.OTHER + " | head -40; "
                        "head -5 _references/gars-bio.conda.txt | cut -c1-80", self.labelled(n=True))

    # each widened shape: (name, command, its admitted output line); red on the frozen rule, green on the amended one
    def widened(self):
        doc, other = self.DOC, self.OTHER
        two = "grep -n Key " + doc + " " + other
        return [
            ("rg -n, two typed files", "rg -n Key " + doc + " " + other, self.labelled(n=True)),
            ("rg, two typed files, unnumbered", "rg -i pinned " + doc + " " + other, self.labelled()),
            ("rg --line-number --no-heading, then head", "rg --line-number --no-heading Key " + doc + " " + other
             + "; head -3 " + other, self.labelled(n=True)),
            ("rg -H, the doc alone", "rg -H -n Key " + doc, self.labelled(n=True)),
            ("rg -H, numbered on a terminal", "rg -H Key " + doc, self.labelled(n=True)),
            ("cd, then rg", "cd /tmp/run-c8021046/gars && rg -n Key " + doc + " " + other, self.labelled(n=True)),
            ("rg as a stdin filter", two + " | rg -i pinned", self.labelled(n=True)),
            ("sed -n on another file", two + "; sed -n 1,5p " + other, self.labelled(n=True)),
            ("sed -n on the doc beside the read", two + "; sed -n 170,180p " + doc, self.labelled(n=True)),
            ("sed -ne, a regex address", two + "; sed -ne /Key/p " + other, self.labelled(n=True)),
            ("sed -n as a filter", two + " | sed -n 1,40p", self.labelled(n=True)),
            ("awk on another file", two + "; awk 'NR>=1 && NR<=3' " + other, self.labelled(n=True)),
            ("awk -F on the doc beside the read", two + "; awk -F: '{print $1}' " + doc, self.labelled(n=True)),
            ("echo between commands", two + "; echo ---; head -3 " + other, self.labelled(n=True)),
            ("echo first", "echo checking && " + two, self.labelled(n=True)),
        ]

    def test_each_widened_shape_is_admitted(self):
        for name, cmd, out in self.widened():
            with self.subTest(name):
                self.both_kinds(cmd, out)

    # od57-gap follow-up: these shapes also read the doc bare, with no other file read unlabelled, so the doc's bare
    # line (or 175: under the grep's -n) is admitted there too
    BARE_BESIDE = ("sed -n on the doc beside the read", "awk -F on the doc beside the read")

    def test_each_widened_shape_refuses_other_bytes_another_label_and_a_glob(self):
        for name, cmd, out in self.widened():
            n = ":175:" in out
            with self.subTest(name, case="an unlabelled line"):
                # od57-line: the unlabelled line is admitted whatever the command; the read rules alone admit it only
                # beside a bare read of the doc, and a byte after it refuses
                body = self.bash_record(cmd, f"{'175:' if n else ''}{self.text}\n")
                self.assertTrue(self.admitted(body))
                with self.reads_only():
                    self.assertEqual(self.admitted(body), name in self.BARE_BESIDE)
                self.assertFalse(self.admitted(self.line_twin(body)))
            for case, body in (
                    ("other bytes", self.labelled(n=n, text=_one_char_off(self.text))),
                    ("a byte after the line", out[:-1] + "x\n"),
                    ("a label to another file", self.labelled(n=n, label=self.OTHER)),
                    ("a context line", f"{self.DOC}-175-{self.text}\n")):
                with self.subTest(name, case=case):
                    self.assertFalse(self.admitted(self.bash_record(cmd, body)))
            # od57-line: `./<doc>` resolves to the doc with no cwd, so od57-line admits the label (retargeted)
            with self.subTest(name, case="a label resolving to the doc but not typed"):
                self.line_retarget(self.bash_record(cmd, self.labelled(n=n, label="./" + self.DOC)))
            globbed = cmd.replace(self.OTHER, "_references/*.txt") if self.OTHER in cmd else cmd + " _references/*.md"
            with self.subTest(name, case="a glob operand"):
                self.line_retarget(self.bash_record(globbed, out))

    def test_everything_else_still_refuses(self):
        doc, other = self.DOC, self.OTHER
        two = "grep -n Key " + doc + " " + other
        cases = {
            "an unlabelled line": (two + "; head -3 " + other, f"175:{self.text}\n"),
            "the bare line": (two + "; head -3 " + other, f"{self.text}\n"),
            "a -h grep": ("grep -h -n Key " + doc + " " + other + "; head " + other, f"175:{self.text}\n"),
            "a single-operand grep then a file": ("grep -n Key " + doc + "; head " + other, f"175:{self.text}\n"),
            "a recursive grep": ("grep -rn Key _references; head " + other, self.labelled(n=True)),
            "a recursive grep beside a typed one": (two + "; grep -rn Key gars", self.labelled(n=True)),
            "a glob operand": ("grep -n Key _references/*.md; head " + other, self.labelled(n=True)),
            "a glob in a later read": (two + "; head _references/*.txt", self.labelled(n=True)),
            "a label that is not the doc": ("grep -n Key a.md " + other + "; head x.md", f"a.md:175:{self.text}\n"),
            "a number other than 175": (two + "; head " + other, f"{doc}:174:{self.text}\n"),
            "a python": (two + "; python3 -c 'print(1)'", self.labelled(n=True)),
            "a second cd": (two + "; cd /tmp; head " + other, self.labelled(n=True)),
            "a shell": (two + "; sh -c 'cat x'", self.labelled(n=True)),
            "a substitution": (two + "; head $(cat x)", self.labelled(n=True)),
            "an input redirect": (two + "; head < " + other, self.labelled(n=True)),
            "a dotdot cd": ("cd ../gars && " + two + "; head " + other, self.labelled(n=True)),
            "a dotdot cd, absolute operands": ("cd ../gars && grep -n Key /tmp/run-c8021046/gars/" + doc + " " + other
                                               + "; head " + other,
                                               self.labelled(n=True, label="/tmp/run-c8021046/gars/" + doc)),
            # rg: no unlabelled read, no folder walk, no filter, no rewrite, no option outside the closed set
            "rg with no file operand": ("rg -n Key", self.labelled(n=True)),
            "rg with no file operand after ;": (two + "; rg -n Key", self.labelled(n=True)),
            "rg -r": ("rg -r X Key " + doc + " " + other, self.labelled()),
            "rg -g": ("rg -n -g x Key " + doc + " " + other, self.labelled(n=True)),
            "rg -u": ("rg -u -n Key " + doc + " " + other, self.labelled(n=True)),
            "rg --pre": ("rg --pre cat -n Key " + doc + " " + other, self.labelled(n=True)),
            "rg -H -I": ("rg -H -I -n Key " + doc + " " + other, self.labelled(n=True)),
            "rg -N, a numbered line": ("rg -N Key " + doc + " " + other, self.labelled(n=True)),
            "rg -n, an unnumbered line": ("rg -n Key " + doc + " " + other, self.labelled()),
            "rg a folder (label from disk)": ("rg -n Key _references " + other, self.labelled(n=True)),
            "rg, the doc alone, a label-shaped line": ("rg -n Key " + doc, self.labelled(n=True)),
            "rg -I, a label-shaped line": ("rg -I -n Key " + doc + " " + other, self.labelled(n=True)),
            "a glob grep beside a typed rg": ("rg -n Key " + doc + " " + other + "; grep -n Key _references/*.md",
                                              self.labelled(n=True)),
            "a recursive grep beside a typed rg": ("rg -n Key " + doc + " " + other + "; grep -rn Key gars",
                                                   self.labelled(n=True)),
            # sed and awk never read as the read: their output carries no typed label
            "sed -n with a label-shaped line": ("sed -n 175p " + doc, self.labelled(n=True)),
            "sed without -n": (two + "; sed 1p " + other, self.labelled(n=True)),
            "sed w": (two + "; sed -n 1w/tmp/x " + other, self.labelled(n=True)),
            "sed -i": (two + "; sed -i -n 1p " + other, self.labelled(n=True)),
            "sed s": (two + "; sed -n s/a/b/p " + other, self.labelled(n=True)),
            "sed e": (two + "; sed -n 1e " + other, self.labelled(n=True)),
            "sed regex with $": (two + '; sed -n "/$X/p" ' + other, self.labelled(n=True)),
            "awk system": (two + "; awk 'BEGIN{system(\"id\")}'", self.labelled(n=True)),
            "awk getline": (two + "; awk '{getline x < \"/etc/x\"; print x}' " + other, self.labelled(n=True)),
            "awk a redirect": (two + "; awk '{print > \"x\"}' " + other, self.labelled(n=True)),
            "awk a pipe": (two + "; awk '{print | \"sh\"}' " + other, self.labelled(n=True)),
            "awk -f": (two + "; awk -f prog.awk " + other, self.labelled(n=True)),
            "awk ENVIRON": (two + "; awk 'BEGIN{print ENVIRON[\"HOME\"]}'", self.labelled(n=True)),
            "echo an expansion": (two + "; echo $HOME", self.labelled(n=True)),
            "echo an escape": (two + "; echo 'a\\x41'", self.labelled(n=True)),
            "echo alone": ("echo " + doc + ":175:x", self.labelled(n=True)),
        }
        # od57-line admits every case below whose line is the doc's label, 175: or bare (retargeted); a label naming
        # another file or another number still refuses as is
        still = ("a label that is not the doc", "a number other than 175")
        for name, (cmd, out) in cases.items():
            with self.subTest(name):
                if name in still:
                    self.assertFalse(self.admitted(self.bash_record(cmd, out)))
                else:
                    self.line_retarget(self.bash_record(cmd, out))

    # od57-gap follow-up (glitch-45, scope 1): the doc's bare line from a read that types the doc as its only file
    # operand, the command naming no other file an unlabelled line could come from.
    # (name, command, its admitted line, the same read with a second file operand, the command plus another file read)
    def bare(self):
        doc, other, t = self.DOC, self.OTHER, self.text
        return [
            ("sed -n", "sed -n 170,180p " + doc, f"{t}\n", "sed -n 170,180p " + doc + " " + other),
            ("rg, no -H", "rg pinned " + doc, f"{t}\n", "rg -I pinned " + doc + " " + other),
            ("rg -n", "rg -n Key " + doc, f"175:{t}\n", "rg -n -I Key " + doc + " " + other),
            ("awk", "awk 'NR==175' " + doc, f"{t}\n", "awk 'NR==175' " + doc + " " + other),
            ("awk, an assignment operand", "awk 'NR==n' n=175 " + doc, f"{t}\n", "awk 'NR==n' n=175 " + doc + " " + other),
            ("head | tail", "head -n 200 " + doc + " | tail -n 30", f"{t}\n", "head -n 200 " + doc + " " + other),
            ("tail +N", "tail -n +170 " + doc, f"{t}\n", "tail -n +170 " + doc + " " + other),
            ("cd, sed ; echo", "cd /tmp/run-c8021046/gars && sed -n 170,180p " + doc + "; echo ---", f"{t}\n",
             "cd /tmp/run-c8021046/gars && sed -n 170,180p " + doc + " " + other + "; echo ---"),
            ("grep -n ; sed", "grep -n Key " + doc + "; sed -n 175p " + doc, f"175:{t}\n",
             "grep -n -h Key " + doc + " " + other + "; sed -n 175p " + doc),
            ("cat && wc", "cat " + doc + " && wc -l " + doc, f"{t}\n", "cat " + doc + " " + other + " && wc -l " + doc),
            ("labelled grep ; bare sed", "grep -n Key " + doc + " " + other + "; sed -n 170,180p " + doc, f"{t}\n",
             "grep -n Key " + doc + " " + other + "; sed -n 170,180p " + doc + " " + other),
        ]

    def test_bare_doc_reads_are_admitted(self):
        for name, cmd, out, _ in self.bare():
            with self.subTest(name):
                self.both_kinds(cmd, out)

    def test_bare_doc_reads_refuse_a_second_file_other_bytes_an_extra_byte_and_a_glob(self):
        for name, cmd, out, second in self.bare():
            n = out.startswith("175:")
            glob = cmd.replace(self.DOC, "_references/*.md")
            cases = (("a second file operand", second, out),
                     ("another file read after it", cmd + "; cat " + self.OTHER, out),
                     ("another file read first", "head -3 " + self.OTHER + " && " + cmd, out),
                     ("other bytes", cmd, f"{'175:' if n else ''}{_one_char_off(self.text)}\n"),
                     ("an extra byte", cmd, out[:-1] + "x\n"),
                     ("a byte before", cmd, " " + out),
                     ("a glob", glob, out),
                     ("a label", cmd, self.labelled(n=n)))
            # od57-line admits the whole line whatever else the command reads, and the doc's label (retargeted);
            # other bytes, a byte after the line and a byte before it still refuse as is
            line = ("a second file operand", "another file read after it", "another file read first", "a glob",
                    "a label")
            for case, c, body in cases:
                with self.subTest(name, case=case):
                    if case in line:
                        self.line_retarget(self.bash_record(c, body))
                    else:
                        self.assertFalse(self.admitted(self.bash_record(c, body)))

    def test_bare_lines_need_a_read_that_prints_the_doc_whole(self):
        # od57-line: the bare line is admitted whatever printed it (retargeted)
        for cmd in ("wc -l " + self.DOC, "cut -c1-80 " + self.DOC, "echo x; wc -c " + self.DOC):
            with self.subTest(cmd):
                self.line_retarget(self.bash_record(cmd, f"{self.text}\n"))

    def test_a_dashdash_or_stdin_operand_refuses(self):
        """REVIEW-OD57-GAP-20261107 MINOR-2: after `--` a file may be named like an option, and `-` is standard input;
        either could supply the bare line, so either refuses the whole command."""
        # od57-line: the bare line is admitted whatever the operands (retargeted)
        for cmd in ("cat -- -notes; cat " + self.DOC, "head -n 5 -- -x " + self.DOC, "cat " + self.DOC + " -"):
            with self.subTest(cmd):
                self.line_retarget(self.bash_record(cmd, f"{self.text}\n"))

    def test_bare_numbered_only_where_n_was_typed(self):
        for cmd in ("sed -n 175p " + self.DOC, "rg pinned " + self.DOC, "cat -n " + self.DOC + " | head",
                    "awk 'NR==175' " + self.DOC + "; echo ---"):
            with self.subTest(cmd):          # od57-line: `175:` is a closed prefix whatever was typed (retargeted)
                self.line_retarget(self.bash_record(cmd, f"175:{self.text}\n"))

    def test_an_agent_or_task_copy_stays_out_of_scope(self):
        """A sub-agent's report quoting the labelled line is no read (a separate gap, not this amendment)."""
        for tool in ("Agent", "Task"):
            with self.subTest(tool):
                body = _cc(_use("toolu_A", tool, {"description": "read", "prompt": "grep -n Key " + self.DOC}),
                           _result("toolu_A", self.labelled(n=True)))
                self.assertFalse(self.admitted(body))

    def test_the_probe_still_refuses_a_second_finding_on_the_line(self):
        for cmd in ("grep -n Key " + self.DOC + " " + self.OTHER + "; head -3 " + self.OTHER,
                    "rg -n Key " + self.DOC + " " + self.OTHER + "; echo ---; sed -n 1,3p " + self.OTHER):
            with self.subTest(cmd):
                out = self.labelled(n=True) + self.OTHER + ":9:PLANTED\n"
                scanner = _Gitleaks(self.text[:40], {"PLANTED": OD57_RULE})
                self.assertFalse(self.admitted(self.bash_record(cmd, out), scanner=scanner))
                self.assertTrue(self.admitted(self.bash_record(cmd, self.labelled(n=True) + self.OTHER + ":9:ok\n"),
                                              scanner=scanner))

    def test_a_write_of_the_doc_first_still_refuses(self):
        for cmd in ("grep -n Key " + self.DOC + " " + self.OTHER + "; head -3 " + self.OTHER,
                    "rg -n Key " + self.DOC + " " + self.OTHER):
            with self.subTest(cmd):
                body = _cc(_use("toolu_W", "Write", {"file_path": "/tmp/run-c8021046/gars/" + self.DOC, "content": "x"}),
                           _result("toolu_W", "ok")) + self.bash_record(cmd, self.labelled(n=True))
                self.assertFalse(self.admitted(body))

    def test_the_frozen_shell_rule_is_unchanged(self):
        """The amendment adds a fallback only: _ruled_shell and _ruled_bash answer as frozen (walk_launch.od57_bound and
        the door's _ruled_bash read them)."""
        from box import od57_rule
        doc = self.DOC
        self.assertTrue(od57_rule._ruled_bash("grep -n Key " + doc + " " + self.OTHER + " | head"))
        # an unlabelled read beside another file read unlabelled: no read at all
        self.assertIsNone(od57_rule._ruled_compound("grep -n Key " + doc + "; head " + self.OTHER))
        for cmd in ("grep -n Key " + doc + " " + self.OTHER + "; echo done", "rg -n Key " + doc + " " + self.OTHER,
                    "grep -n Key " + doc + " " + self.OTHER + "; head " + self.OTHER):
            with self.subTest(cmd):
                self.assertIsNone(od57_rule._ruled_shell(cmd))
                self.assertIsNotNone(od57_rule._ruled_compound(cmd))


for _name in [n for n in vars(TestOD57Chain) if n.startswith("test_")]:
    setattr(TestOD57Gap, _name, None)  # TestOD57Chain's own tests run once, in their own class


class TestOD57GapCodex(TestOD57Ruling):
    """od57-gap through the read shapes (arm O): the compound read inside Codex's `/bin/bash -lc` wrapper, in the turn
    stream's command_execution and in the rollout's CommandExecution and its exec output copy."""

    DOC = "_references/environment.md"
    OTHER = "_references/gars-bio.lock.txt"

    def scan(self, files, scanner=None):
        scanner = scanner or _Gitleaks(self.text[:40])
        return sr.scan(files, SECRETS, rules_scanner=scanner, read_shapes=CODEX_SHAPES), scanner

    def outcome(self, name, body, kind):
        p = self.write(name, body)
        r, _ = self.scan([(p, kind)])
        return sorted(x["line"] for x in r["ruled"]), sorted(x["line"] for x in r["refused"])

    def stream(self, cmd, out):
        command = _cx_wrap(cmd)
        return _cc({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
                   _cx_item("item.started", "item_1", command, "", "in_progress"),
                   _cx_item("item.completed", "item_1", command, out))

    def rollout(self, cmd, out):
        return _cc(_cx_meta(), _cx_custom(1, "call-o1"), _cx_end(2, "exec-cmd-1", ["/bin/bash", "-lc", cmd], out),
                   _cx_custom_out(3, "call-o1", f"Script completed\n{out}exit code 0"))

    def cases(self):
        doc, other = self.DOC, self.OTHER
        good = f"{doc}:175:{self.text}\n"
        return [("rg -n, two files", "rg -n Key " + doc + " " + other, good),
                ("sed -n, the doc bare", "sed -n 170,180p " + doc, f"{self.text}\n"),
                ("grep ; sed -n", "grep -n Key " + doc + " " + other + "; sed -n 1,5p " + other, good),
                ("grep ; echo ; head", "grep -n Key " + doc + " " + other + "; echo ---; head -3 " + other, good)]

    def test_codex_compound_reads_are_admitted(self):
        for name, cmd, out in self.cases():
            with self.subTest(name):
                self.assertFalse(sr._ruled_bash(cmd))
                self.assertEqual(self.outcome("turn-1.jsonl", self.stream(cmd, out), "stream"), ([4], []))
                self.assertEqual(self.outcome("rollout.jsonl", self.rollout(cmd, out), "session"), ([3, 4], []))

    def test_codex_compound_refusals(self):
        # od57-line: a whole line of the shell's output after `175:` or the doc's label is admitted whatever the
        # command or the wrapper (retargeted, TestOD57Ruling.od57_line); other bytes and another label still refuse
        def refuses(name, kind, line):
            return lambda b: self.assertEqual(self.outcome(name, b, kind), ([], [line]))

        def admits(name, kind, line):
            return lambda b: self.assertEqual(self.outcome(name, b, kind), ([line], []))
        for name, cmd, out in self.cases():
            bare = "bare" in name
            for case, body in (("other bytes", f"{self.DOC}:175:{_one_char_off(self.text)}\n"),
                               ("another label", f"{self.OTHER}:175:{self.text}\n")):
                with self.subTest(name, case=case):
                    self.assertEqual(self.outcome("turn-1.jsonl", self.stream(cmd, body), "stream")[0], [])
            with self.subTest(name, case="unlabelled" if not bare else "a bare 175: with no -n"):
                self.od57_line(refuses("turn-1.jsonl", "stream", 4), admits("turn-1.jsonl", "stream", 4),
                               self.stream(cmd, f"175:{self.text}\n"))
            with self.subTest(name, case="a second file operand" if bare else "a glob operand"):
                globbed = cmd + " " + self.OTHER if bare else cmd.replace(self.OTHER, "_references/*.txt")
                self.od57_line(refuses("turn-1.jsonl", "stream", 4), admits("turn-1.jsonl", "stream", 4),
                               self.stream(globbed, out))
        # the wrapper itself is unchanged for the read rules: -c, another shell, or more words still refuse there
        cmd, out = self.cases()[0][1], self.cases()[0][2]
        for argv in (["/bin/bash", "-c", cmd], ["/bin/zsh", "-lc", cmd], ["/bin/bash", "-lc", cmd, "x"]):
            with self.subTest(argv=argv):
                body = _cc(_cx_meta(), _cx_end(1, "exec-cmd-1", argv, out))
                self.od57_line(refuses("rollout.jsonl", "session", 2), admits("rollout.jsonl", "session", 2), body)


class TestOD57Line(TestOD57Ruling):
    """od57-line (SCANREFUSAL-ROAD-20261108, candidate 3 narrowed; Javier's word pending): the 80 pinned bytes as a
    whole output line of a Bash, BashOutput, Read or Grep call (or a read shape's tool), after exactly one of a closed
    list of prefixes, whatever the command. The STOP4 shape (s-91dbb18a: `175:<80 bytes>` in a Bash tool_result's
    content and its toolUseResult stdout, suffix 0) is built from closed features only; the commands are synthetic."""

    DOC = "_references/environment.md"
    OTHER = "_references/gars-bio.lock.txt"

    def outcome(self, body, kind="transcript", scanner=None, name=None):
        p = self.write(name or f"{kind}.jsonl", body)
        r, _ = self.scan([(p, kind)], scanner)
        return sorted(x["line"] for x in r["ruled"]), sorted(x["line"] for x in r["refused"])

    def commands(self):
        doc = self.DOC
        return [("find -exec grep -n", "find . -name environment.md -exec grep -n Key {} +"),
                ("xargs grep -n", "ls " + doc + " | xargs grep -n Key"),
                ("a for loop", "for f in " + doc + " " + self.OTHER + "; do grep -n Key \"$f\"; done"),
                ("python3 -c", "python3 -c 'print(open(\"" + doc + "\").read())' | grep -n Key"),
                ("a globbed grep", "grep -n Key _references/*.md"),
                ("bash -c", "bash -c 'grep -n Key " + doc + "'"),
                ("a heredoc", "cat <<'EOF' | sh\ngrep -n Key " + doc + "\nEOF")]

    def stop4(self, cmd, prefix="175:", tail="\n", side=False, text=None):
        return self.bash_record(cmd, f"{prefix}{self.text if text is None else text}{tail}", side)

    # ---------------------------------------------------------------------------------------------- admitted
    def test_the_stop4_shape_is_admitted_whatever_the_command(self):
        for name, cmd in self.commands():
            for kind, side in (("transcript", False), ("stream", True)):
                with self.subTest(name, kind=kind):
                    self.assertFalse(sr._ruled_bash(cmd))                    # no read rule admits the command
                    self.assertEqual(self.outcome(self.stop4(cmd, side=side), kind), ([2], []))

    def test_every_listed_prefix_is_admitted(self):
        abs_doc = self.doc
        for prefix in ("", "175:", "175\t", "   175\t", "175→", abs_doc + ":", abs_doc + ":175:", self.DOC + ":",
                       self.DOC + ":175:", "gars/" + self.DOC + ":175:"):
            with self.subTest(prefix=prefix):
                self.assertEqual(self.outcome(self.stop4("grep -rn Key .", prefix=prefix)), ([2], []))

    def test_the_line_among_other_output_lines_is_admitted(self):
        out = f"12:first\n175:{self.text}\n200:last\n"
        self.assertEqual(self.outcome(self.bash_record("grep -rn Key .", out)), ([2], []))

    def test_bash_output_and_cat_n_results_are_admitted(self):
        cases = (("BashOutput", "BashOutput", {"bash_id": "b1"}, f"175:{self.text}\n", {"stdout": f"175:{self.text}"}),
                 ("cat -n of a copy", "Bash", {"command": "cat -n /tmp/copy.md"}, f"   175\t{self.text}\n", None))
        for name, tool, inp, out, tur in cases:
            with self.subTest(name):
                body = _cc(_use("toolu_Z", tool, inp), _result("toolu_Z", out, tur))
                self.assertEqual(self.outcome(body), ([2], []))

    def test_the_seventh_of_november_shapes_are_still_admitted(self):
        doc = self.DOC
        for cmd, out in (
                ("grep -i pinned " + doc + " _references/gars-bio.conda.txt; grep -i pinned README.md " + doc
                 + " docs/setup.md | head -20", f"{doc}:{self.text}\n"),
                ("cd /tmp/run-c8021046/gars && grep -n Key " + doc + " " + self.OTHER + " | head -40; "
                 "head -5 _references/gars-bio.conda.txt | cut -c1-80", f"{doc}:175:{self.text}\n"),
                ("sed -n 170,180p " + doc, f"{self.text}\n"),
                (f"grep -n pinned {self.doc}", f"175:{self.text}\n")):
            with self.subTest(cmd=cmd[:30]):
                self.assertEqual(self.outcome(self.bash_record(cmd, out)), ([2], []))
        self.assertEqual(self.outcome(self.read_record()), ([3], []))

    # ---------------------------------------------------------------------------------------------- refused
    def test_a_trailing_byte_refuses(self):
        for tail in (" ", "x\n", "\r\n", " # note\n", "\t\n"):
            with self.subTest(tail=tail):
                self.assertEqual(self.outcome(self.stop4("grep -rn Key .", tail=tail)), ([], [2]))

    def test_a_different_prefix_refuses(self):
        for prefix in ("176:", "175-", "175: ", " 175:", "1175:", "x", "README.md:175:", self.OTHER + ":175:",
                       "./../" + self.DOC + ":175:", "../" + self.DOC + ":", "/tmp/run-dead/x/" + self.DOC + ":",
                       "a" * 300 + ":175:", "api_key=zz9f3c2a1b7e6d5c4b3a2f1e:", self.DOC + ":175:175:",
                       self.DOC + "-175-", "--", "175\t\t"):
            with self.subTest(prefix=prefix[:40]):
                self.assertEqual(self.outcome(self.stop4("grep -rn Key .", prefix=prefix)), ([], [2]))

    def test_one_changed_byte_refuses(self):
        self.assertEqual(self.outcome(self.stop4("grep -rn Key .", text=_one_char_off(self.text))), ([], [2]))

    def test_the_bytes_inside_a_longer_line_refuse(self):
        for prefix, tail in (("", " and more\n"), ("175:x", "\n"), ("noise ", " noise\n")):
            with self.subTest(prefix=prefix, tail=tail):
                self.assertEqual(self.outcome(self.stop4("grep -rn Key .", prefix=prefix, tail=tail)), ([], [2]))

    def test_the_bytes_split_across_two_lines_refuse(self):
        half = len(self.text) // 2
        out = f"175:{self.text[:half]}\n{self.text[half:]}\n"
        p = self.write("transcript.jsonl", self.bash_record("grep -rn Key .", out))
        r, _ = self.scan([(p, "transcript")], _Gitleaks(self.text[:20]))
        self.assertEqual(r["ruled"], [])
        self.assertEqual([x["line"] for x in r["refused"]], [2])

    def test_a_write_of_the_doc_first_refuses(self):
        for tool in ("Write", "Edit"):
            with self.subTest(tool=tool):
                body = _cc(_use("toolu_W", tool, {"file_path": self.doc, "content": "x"}),
                           _result("toolu_W", "ok"), _use("toolu_B", "Bash", {"command": "grep -rn Key ."}),
                           _result("toolu_B", f"175:{self.text}\n", {"stdout": f"175:{self.text}"}))
                self.assertEqual(self.outcome(body), ([], [4]))
        # the same file with the write after the line: admitted
        body = _cc(_use("toolu_B", "Bash", {"command": "grep -rn Key ."}),
                   _result("toolu_B", f"175:{self.text}\n", {"stdout": f"175:{self.text}"}),
                   _use("toolu_W", "Write", {"file_path": self.doc, "content": "x"}))
        self.assertEqual(self.outcome(body), ([2], []))

    def test_a_raw_count_mismatch_refuses(self):
        t = self.text
        cases = {
            "the agent's own text beside the result": _cc(
                _use("toolu_B", "Bash", {"command": "grep -rn Key ."}),
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "toolu_B", "content": f"175:{t}\n"},
                    {"type": "text", "text": t}]}}),
            "a second copy under another key": _cc(
                _use("toolu_B", "Bash", {"command": "grep -rn Key ."}),
                dict(_result("toolu_B", f"175:{t}\n", {"stdout": f"175:{t}"}), note=t)),
            "a second copy inside a longer string of the result": _cc(
                _use("toolu_B", "Bash", {"command": "grep -rn Key ."}),
                _result("toolu_B", f"175:{t}\n", {"stdout": f"175:{t}", "stderr": f"warn {t} again"})),
            "an Agent result beside a Bash result": _cc(
                _use("toolu_B", "Bash", {"command": "grep -rn Key ."}),
                _use("toolu_A", "Agent", {"prompt": "read it"}),
                {"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "toolu_B", "content": f"175:{t}\n"},
                    {"type": "tool_result", "tool_use_id": "toolu_A", "content": f"{t}\n"}]}}),
        }
        for name, body in cases.items():
            with self.subTest(name):
                ruled, refused = self.outcome(body)
                self.assertEqual(ruled, [])
                self.assertEqual(len(refused), 1)

    def test_a_json_escaped_copy_refuses(self):
        # a record whose raw bytes hold the text only escaped: the decoded and raw counts disagree
        t = self.text
        rec = json.dumps(_result("toolu_B", f"175:{t}\n", {"stdout": f"175:{t}"}), ensure_ascii=True)
        body = _cc(_use("toolu_B", "Bash", {"command": "grep -rn Key ."})) + rec.replace(" ", "\\u0020").encode() \
            + b"\n"
        p = self.write("transcript.jsonl", body)
        r, _ = self.scan([(p, "transcript")], _Gitleaks("Key"))
        self.assertEqual(r["ruled"], [])

    def test_tools_off_the_whitelist_refuse(self):
        t = self.text
        cases = {
            "an Agent result": _cc(_use("toolu_A", "Agent", {"prompt": "x"}), _result("toolu_A", f"{t}\n")),
            "a Task result": _cc(_use("toolu_A", "Task", {"prompt": "x"}), _result("toolu_A", f"175:{t}\n")),
            "a WebFetch result": _cc(_use("toolu_A", "WebFetch", {"url": "https://x"}),
                                     _result("toolu_A", f"{t}\n")),
            "a Read of another file": _cc(_use("toolu_A", "Read", {"file_path": "/tmp/run-c8021046/gars/" + self.OTHER}),
                                          _result("toolu_A", f"   175\t{t}\n")),
            "a Read of a lookalike run tree": _cc(_use("toolu_A", "Read", {"file_path": "/tmp/run-dead/x/" + self.DOC}),
                                                  _result("toolu_A", f"   175\t{t}\n")),
            "a Grep of another file": _cc(_use("toolu_A", "Grep", {"pattern": "Key", "output_mode": "content",
                                                                    "path": self.OTHER}),
                                          _result("toolu_A", f"175:{t}\n")),
            "a result with no call": _cc(_result("toolu_X", f"175:{t}\n")),
            "a result whose call appears twice": _cc(_use("toolu_B", "Bash", {"command": "ls"}),
                                                     _use("toolu_B", "Bash", {"command": "ls"}),
                                                     _result("toolu_B", f"175:{t}\n")),
            "the agent's own text": _cc({"type": "assistant", "message": {"content": [
                {"type": "text", "text": f"175:{t}\n"}]}}),
            "a tool_use input": _cc(_use("toolu_B", "Bash", {"command": f"echo '{t}'"})),
        }
        for name, body in cases.items():
            with self.subTest(name):
                ruled, refused = self.outcome(body)
                self.assertEqual(ruled, [])
                self.assertEqual(len(refused), 1)

    def test_a_non_agent_kind_refuses_the_line(self):
        for kind in ("ledger", "evidence", "preflight", "launch"):
            with self.subTest(kind=kind):
                self.assertEqual(self.outcome(self.stop4("grep -rn Key ."), kind)[0], [])
                data = self.stop4("grep -rn Key .")
                rec = data.split(b"\n")[1]
                self.assertIsNone(sr._od57._any_text(json.loads(rec), rec, sr._od57._tool_uses(data), (), (), kind,
                                                     sr.RULED_LINES[0]))

    def test_another_rule_or_a_second_finding_on_the_line_refuses(self):
        body = self.stop4("grep -rn Key .")
        self.assertEqual(self.outcome(body, scanner=_Gitleaks(self.text[:40], {self.text[:20]: "curl-auth-header"})),
                         ([2], [2]))
        out = f"175:{self.text}\napi_key_SECOND\n"
        body = self.bash_record("grep -rn Key .", out)
        self.assertEqual(self.outcome(body, scanner=_Gitleaks(self.text[:40], {"api_key_SECOND": OD57_RULE})),
                         ([], [2, 2]))

    # ---------------------------------------------------------------------------------------------- vendor shapes
    def test_codex_stream_and_rollout_any_command(self):
        cmd = "find . -name environment.md -exec grep -n Key {} +"
        out = f"175:{self.text}\n"
        stream = _cc({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
                     _cx_item("item.started", "item_1", _cx_wrap(cmd), "", "in_progress"),
                     _cx_item("item.completed", "item_1", _cx_wrap(cmd), out))
        rollout = _cc(_cx_meta(), _cx_custom(1, "call-o1"), _cx_end(2, "exec-cmd-1", ["/bin/bash", "-lc", cmd], out),
                      _cx_custom_out(3, "call-o1", f"Script completed\n{out}exit code 0"))

        def run(body, kind, name):
            p = self.write(name, body)
            r = sr.scan([(p, kind)], SECRETS, rules_scanner=_Gitleaks(self.text[:40]), read_shapes=CODEX_SHAPES)
            return sorted(x["line"] for x in r["ruled"]), sorted(x["line"] for x in r["refused"])
        self.assertEqual(run(stream, "stream", "turn-1.jsonl"), ([4], []))
        self.assertEqual(run(rollout, "session", "rollout.jsonl"), ([3, 4], []))
        bad = out.replace("175:", "176:")
        stream_bad = _cc({"type": "thread.started", "thread_id": "thread-1"}, {"type": "turn.started"},
                         _cx_item("item.completed", "item_1", _cx_wrap(cmd), bad))
        self.assertEqual(run(stream_bad, "stream", "turn-1.jsonl"), ([], [3]))

    # ---------------------------------------------------------------------------------------------- mutants
    def test_mutation_witnesses_of_the_od57_line_guards(self):
        t = self.text
        bash = "grep -rn Key ."
        cases = (
            ("the prefix set opened", self.stop4(bash, prefix="176:"), "_any_prefix_ok",
             ('if prefix in ("", "175:")', 'if True or prefix in ("", "175:")')),
            ("the label resolve dropped", self.stop4(bash, prefix="README.md:175:"), "_any_prefix_ok",
             ("_resolves_to_doc(prefix[:-len(tail)])", "True")),
            ("the tool whitelist dropped", _cc(_use("toolu_A", "Agent", {"prompt": "x"}),
                                               _result("toolu_A", f"{t}\n")), "_any_claude_strings",
             ("got[0][0] in _ANY_CLAUDE_TOOLS", "True")),
            ("one call per id dropped", _cc(_use("toolu_B", "Bash", {"command": "ls"}),
                                            _use("toolu_B", "Bash", {"command": "ls"}),
                                            _result("toolu_B", f"175:{t}\n")), "_any_claude_strings",
             ("and len(got) == 1 ", "")),
            ("the kind gate dropped", None, "_any_text", ("kind not in AGENT_TEXT_KINDS or ", "")),
            ("the decoded count dropped", _cc(_use("toolu_B", "Bash", {"command": bash})) + json.dumps(
                dict(_result("toolu_B", f"175:{t}\n"), note="NOTE")).replace(
                "NOTE", t.replace(" ", "\\u0020")).encode() + b"\n", "_any_text",
             ("sum(x.count(found) for x in _strings(rec, [])) != hits", "False")),
            ("the T1 write check dropped", _cc(_use("toolu_W", "Write", {"file_path": self.doc, "content": "x"}),
                                               _result("toolu_W", "ok"), _use("toolu_B", "Bash", {"command": bash}),
                                               _result("toolu_B", f"175:{t}\n")), "ruled_text",
             ("if writes is not None and writes <= line:", "if False:")),
            ("the 80-byte pin dropped", self.stop4(bash, text=_one_char_off(t)), "_line_text",
             ('if _sha(rest) != ruling["sha256"]:', "if False:")),
        )
        for name, body, fn, edit in cases:
            with self.subTest(name):
                if body is None:          # scan_record never hands a non-agent kind over: witnessed on the function
                    data = self.stop4(bash)
                    rec = data.split(b"\n")[1]
                    args = (json.loads(rec), rec, sr._od57._tool_uses(data), (), ())
                    self.assertIsNotNone(sr._od57._any_text(*args, "transcript", sr.RULED_LINES[0]))
                    self.assertIsNone(sr._od57._any_text(*args, "ledger", sr.RULED_LINES[0]))
                    with _mutant(fn, edit):
                        self.assertIsNotNone(sr._od57._any_text(*args, "ledger", sr.RULED_LINES[0]))
                    red(f"od57-line: {name}")
                    continue
                kind = "transcript"
                scanner = _Gitleaks(t[:20]) if "pin" in name else None
                self.assertEqual(self.outcome(body, kind, scanner)[0], [])
                with _mutant(fn, edit):
                    self.assertNotEqual(self.outcome(body, kind, scanner)[0], [], f"{name}: the mutant still refuses")
                red(f"od57-line: {name}")
        # the fallback itself: the STOP4 shape refuses without it
        with _mutant("ruled_text", ("return _any_text(rec, body, uses, shapes, indexes, kind, ruling)", "return None")):
            self.assertEqual(self.outcome(self.stop4(bash)), ([], [2]))
        red("od57-line: the fallback removed (the STOP4 shape refused)")

    # ---------------------------------------------------------------------------------------------- the vendor filter
    def test_the_vendor_tool_filter_keeps_path_and_grep_tools_out(self):
        """REVIEW-OD57-LINE-20261108 F2: _ANY_SHAPE_KINDS admits only a vendor shape's shell tools and their output
        copy. A Gemini session read_file of another path, or a grep_search of another folder, printing the line as a
        whole output line refuses; with the filter widened to the path and grep kinds both are admitted (red); the
        shell tool's same output is admitted (the positive control); an identity edit changes nothing (null)."""
        out = f"175:{self.text}\n"
        cases = (("read_file of another path", "read_file", {"file_path": "/etc/other"}),
                 ("grep_search of another folder", "grep_search", {"pattern": "Key", "dir_path": "/etc"}))

        def run(tool, args):
            body = _cc(GEM_HEAD, _gem_message("msg-g1", [_gem_call("call-g1", tool, args, out)]))
            p = self.write("session.jsonl", body)
            r = sr.scan([(p, "session")], SECRETS, rules_scanner=_Gitleaks(self.text[:40]), read_shapes=GEM_SHAPES)
            return sorted(x["line"] for x in r["ruled"]), sorted(x["line"] for x in r["refused"])
        self.assertEqual(run("run_shell_command", {"command": "find . -exec grep -n Key {} +"}), ([2], []))
        same = ('tool["kind"] not in _ANY_SHAPE_KINDS', 'tool["kind"] not in _ANY_SHAPE_KINDS')
        widen = ('tool["kind"] not in _ANY_SHAPE_KINDS', 'tool["kind"] not in _ANY_SHAPE_KINDS + ("path", "grep")')
        for name, tool, args in cases:
            with self.subTest(name):
                self.assertEqual(run(tool, args), ([], [2]))
                with _mutant("_any_shape_strings", same):
                    self.assertEqual(run(tool, args), ([], [2]))
                with _mutant("_any_shape_strings", widen):
                    self.assertEqual(run(tool, args), ([2], []), f"{name}: the widened filter still refuses")
                red(f"od57-line: the vendor tool filter widened to path and grep ({name})")

    def test_the_null_mutant_stays_green(self):
        with _mutant("_any_text", ("found, hits = None, 0", "found, hits = None, 0")), \
                _mutant("_any_prefix_ok", ('for tail in (":175:", ":"):', 'for tail in (":175:", ":"):')):
            self.assertEqual(self.outcome(self.stop4("grep -rn Key .")), ([2], []))
            self.assertEqual(self.outcome(self.stop4("grep -rn Key .", prefix="176:")), ([], [2]))


for _name in [n for n in vars(TestOD57Ruling) if n.startswith("test_")]:
    setattr(TestOD57GapCodex, _name, None)  # TestOD57Ruling's own tests run once, in their own class
    setattr(TestOD57Line, _name, None)

for _cls_from in (TestOD57OtherArms, TestB17ReadShapes, TestB17Round3, TestB17Round4, TestB17Round5, TestB17Round6):
    for _name in [n for n in vars(_cls_from) if n.startswith("test_")]:
        setattr(TestB20GitReads, _name, None)  # each earlier class's tests run once, in their own class

if __name__ == "__main__":
    unittest.main(verbosity=2)
