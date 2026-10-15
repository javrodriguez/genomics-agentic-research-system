"""box/rules_scanner.py: the pinned gitleaks adapter, with a fake runtime (no scanner runs here).

The pin is bound to what the stub takes measured on athena; a stand-in binary is pinned only by patching the module's
sha256 in memory, inside each test.
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from box import rules_scanner as rs, run_take as rt, scan_record  # noqa: E402

RUNS = STUDY.parents[1] / "lane-reports" / "stub-take-20261014"


class Fake:
    def __init__(self, findings=None, version="8.30.1\n", rc=0, write=True):
        self.calls, self.findings, self.version, self.rc, self.write = [], findings or {}, version, rc, write

    def run(self, argv, *, env=None, timeout=None):
        self.calls.append(list(argv))
        if argv[1] == "version":
            return rt.Completed(0, self.version, "")
        report = argv[argv.index("--report-path") + 1]
        if self.write:
            Path(report).write_text(json.dumps(self.findings.get(argv[2], [])))
        return rt.Completed(self.rc, "", "")


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="rs-")
        self.bin = os.path.join(self.d, "gitleaks")
        Path(self.bin).write_bytes(b"stand-in binary")
        self.sha = hashlib.sha256(b"stand-in binary").hexdigest()
        self.reports = os.path.join(self.d, "reports")
        os.mkdir(self.reports)
        self.f = os.path.join(self.d, "turn-1.jsonl")
        Path(self.f).write_text("{}\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def scanner(self, fake, **kw):
        with mock.patch.object(rs, "GITLEAKS_SHA256", self.sha):
            return rs.gitleaks_scanner(fake, self.reports, **{"binary": self.bin, **kw})


class Pin(unittest.TestCase):
    def test_the_pin_is_what_the_stub_takes_measured_on_athena(self):
        seen = set()
        for name in ("stub-take-run1.json", "stub-take-run2.json", "stub-take-run3.json", "stub-take-run4.json"):
            g = json.loads((RUNS / name).read_text())["gitleaks"]
            seen.add((g["binary"], g["sha256"], g["version"]))
        self.assertEqual(seen, {(rs.GITLEAKS_PATH, rs.GITLEAKS_SHA256, rs.GITLEAKS_VERSION)})
        self.assertEqual(rs.GITLEAKS_VERSION, "8.30.1")


class Adapter(Base):
    def test_findings_by_path_line_and_rule(self):
        fake = Fake({self.f: [{"RuleID": "github-pat", "StartLine": 1, "Match": "REDACTED"}]})
        got = self.scanner(fake)([self.f])
        self.assertEqual(got, [{"path": self.f, "line": 1, "rule": "github-pat"}])
        self.assertEqual(fake.calls[0], [self.bin, "version"])
        self.assertEqual(fake.calls[1], [self.bin, "dir", self.f, "--no-banner", "--redact", "--ignore-gitleaks-allow",
                                         "--report-format", "json",
                                         "--report-path", os.path.join(self.reports, "gitleaks-1.json"),
                                         "--exit-code", "0", "--log-level", "warn"])

    def test_a_clean_file_and_a_null_report(self):
        fake = Fake({self.f: None})
        self.assertEqual(self.scanner(fake)([self.f]), [])

    def test_it_feeds_scan_record(self):
        fake = Fake({self.f: [{"RuleID": "generic-api-key", "StartLine": 1}]})
        res = scan_record.scan([(self.f, "stream")], [("token", "f" * 32)], rules_scanner=self.scanner(fake))
        self.assertEqual([r["why"] for r in res["refused"]], ["the rules scanner's rule 'generic-api-key'"])


class Refusals(Base):
    def test_not_the_pinned_binary(self):
        with self.assertRaises(rs.ScannerRefused):
            rs.gitleaks_scanner(Fake(), self.reports, binary=self.bin)       # the real pin: the stand-in differs
        os.symlink(self.bin, os.path.join(self.d, "link"))
        for b in (os.path.join(self.d, "link"), os.path.join(self.d, "absent"), "relative/gitleaks"):
            with self.subTest(b=b), self.assertRaises((rs.ScannerRefused, rt.Refused)):
                self.scanner(Fake(), binary=b)

    def test_not_the_pinned_version(self):
        self.scanner(Fake())                                      # the pinned version builds (the folder is empty)
        for v in ("8.30.0\n", "v8.30.1\n", "8.30.1 extra\n", ""):
            with self.subTest(v=v), self.assertRaises(rs.ScannerRefused):
                self.scanner(Fake(version=v))

    def test_a_failed_scan_is_never_clean(self):
        for fake in (Fake(rc=1), Fake(write=False), Fake({self.f: {"not": "a list"}}),
                     Fake({self.f: [{"RuleID": "", "StartLine": 1}]}), Fake({self.f: [{"RuleID": "r", "StartLine": 0}]}),
                     Fake({self.f: [{"RuleID": "r", "StartLine": True}]})):
            self.reports = tempfile.mkdtemp(dir=self.d)          # a fresh, empty report folder per case
            scan = self.scanner(fake)                             # built cleanly: only the scan may refuse
            with self.subTest(fake=vars(fake)), self.assertRaises(rs.ScannerRefused):
                scan([self.f])

    def test_a_timeout_is_never_clean(self):
        class Slow(Fake):
            def run(self, argv, *, env=None, timeout=None):
                if argv[1] == "dir":
                    raise TimeoutError("gitleaks timed out")
                return super().run(argv, env=env, timeout=timeout)
        scan = self.scanner(Slow())
        with self.assertRaises(rs.ScannerRefused):
            scan([self.f])

    def test_a_used_report_folder_refuses(self):
        Path(self.reports, "old.json").write_text("[]")
        with self.assertRaises(rs.ScannerRefused):
            self.scanner(Fake())


if __name__ == "__main__":
    unittest.main()
