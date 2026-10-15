"""Bounded, no-process refusal witnesses for directory byte-bound admission."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

PATH = Path(__file__).resolve().parents[3] / "ops/gap4_staging_admission.py"
SPEC = importlib.util.spec_from_file_location("gap_staging_admission_test", PATH)
admission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admission)


def success_stderr(n, leaks=1):
    return ("\x1b[90m10:34PM\x1b[0m \x1b[32mINF\x1b[0m \x1b[1mscanned ~%d bytes (1.30 MB) in 231ms\x1b[0m\n"
            "\x1b[90m10:34PM\x1b[0m \x1b[33mWRN\x1b[0m \x1b[1mleaks found: %d\x1b[0m\n" % (n, leaks))


class DirectoryAdmission(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.tree = Path(self.temporary.name)
        controls = tempfile.TemporaryDirectory()
        self.addCleanup(controls.cleanup)
        self.control = Path(controls.name)
        self.cwd = self.control / "scanner-cwd"
        self.cwd.mkdir(mode=0o700)
        config = self.cwd / "defaults.toml"
        config.write_bytes(admission.DEFAULT_CONFIG)
        scanner = self.control / "scanner"
        scanner.write_bytes(b"synthetic scanner identity")
        patcher = mock.patch.object(admission, "SCANNER", str(scanner))
        patcher.start()
        self.addCleanup(patcher.stop)
        file = self.tree / admission.APPROVED_PATH
        file.parent.mkdir(parents=True)
        span = b"synthetic harmless version prose".ljust(80, b" ")
        data = b"\n" * 174 + span + b"\n"
        file.write_bytes(data)
        file.chmod(0o644)
        digest = hashlib.sha256(data).hexdigest()
        span_digest = hashlib.sha256(span).hexdigest()
        for name, value in (("APPROVED_FILE_BYTES", len(data)), ("APPROVED_FILE_SHA", digest),
                            ("APPROVED_SPAN_SHA", span_digest)):
            patcher = mock.patch.object(admission, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.manifest = {"source_pin": admission.SOURCE_PIN, "tree": str(self.tree),
                         "files": [{"path": admission.APPROVED_PATH, "bytes": len(data),
                                    "mode": 0o644, "sha256": digest}],
                         "directories": [{"path": p.relative_to(self.tree).as_posix(),
                                          "mode": p.stat().st_mode & 0o777}
                                         for p in sorted(self.tree.rglob("*")) if p.is_dir()]}
        self.scan = {"exit": 1, "argv": [str(scanner), "dir", "--no-banner",
                     "--redact", "--config", str(config), "--exit-code", "1", "--ignore-gitleaks-allow", "--gitleaks-ignore-path",
                     "/dev/null", str(self.tree), "--report-format", "json", "--report-path", "/raw.json"],
                     "context": {"cwd": str(self.cwd), "env": {"PATH": "/usr/bin:/bin", "HOME": str(self.cwd)},
                                 "config_path": str(config), "config_sha256": hashlib.sha256(admission.DEFAULT_CONFIG).hexdigest(),
                                 "scanner_sha256": hashlib.sha256(scanner.read_bytes()).hexdigest(),
                                 "scanner_version": admission.SCANNER_VERSION}}
        self.findings = [{"File": str(file), "RuleID": admission.APPROVED_RULE, "StartLine": 175,
                          "EndLine": 175, "StartColumn": 2, "EndColumn": 38, "Secret": "REDACTED",
                          "Fingerprint": str(file) + ":generic-api-key:175"}]
        self.rules = [(admission.APPROVED_PATH, admission.APPROVED_RULE, 1, span_digest)]
        # The exact v8.30.0 success shape as retained from the real 13 Oct run (ANSI colours included), with this
        # fixture's byte total; the report bytes and tree inventory are bound into the scan record.
        self.scan["stderr"] = success_stderr(len(data))
        self.report = json.dumps(self.findings).encode()
        self.scan["report_sha256"] = hashlib.sha256(self.report).hexdigest()
        self.scan["finding_count"] = 1
        self.scan["tree_inventory_sha256"] = admission.inventory_sha256(admission.inventory(self.tree))
        self.scan["tree_inventory_sha256_after"] = self.scan["tree_inventory_sha256"]
        self.scan["scanner_sha256_after"] = self.scan["context"]["scanner_sha256"]

    def run_admission(self, manifest=None, scan=None, findings=None, rules=None, report=None):
        scan = copy.deepcopy(self.scan if scan is None else scan)
        if findings is not None and report is None:   # a changed report, bound like a real one
            report = json.dumps(findings).encode()
            scan["report_sha256"] = hashlib.sha256(report).hexdigest()
            scan["finding_count"] = len(findings) if isinstance(findings, list) else None
        return admission.admit_directory_finding(self.tree,
            self.manifest if manifest is None else manifest, scan,
            self.report if report is None else report,
            managed_rulings=self.rules if rules is None else rules)

    def test_one_exact_approval_keeps_raw_refusal_truth(self):
        result = self.run_admission()
        self.assertEqual(result["raw_scan_exit"], 1)
        self.assertEqual(result["status"], "owner-approved-byte-bound-finding")
        self.assertEqual((result["approved_findings"], result["unresolved_findings"]), (1, 0))

    def test_identical_managed_rulings_are_one_byte_approval(self):
        result = self.run_admission(rules=self.rules * 2)
        self.assertEqual(result["approved_findings"], 1)
        self.assertEqual(result["managed_ruling_count"], 2)
        self.assertEqual(result["matching_managed_ruling_count"], 2)

    def test_config_environment_and_scanner_identity_drift_refuse(self):
        for key, value in (("env", {"GITLEAKS_CONFIG": "/other"}),
                           ("scanner_version", "unknown"), ("scanner_sha256", "0" * 64),
                           ("config_sha256", "0" * 64)):
            changed = copy.deepcopy(self.scan)
            changed["context"][key] = value
            with self.subTest(field=key), self.assertRaises(admission.Refused):
                self.run_admission(scan=changed)
        config = self.cwd / "defaults.toml"
        config.write_bytes(b"[extend]\nuseDefault = true\ndisabledRules = ['generic-api-key']\n")
        with self.assertRaises(admission.Refused):
            self.run_admission()
        config.write_bytes(admission.DEFAULT_CONFIG)
        (self.cwd / "unexpected").write_text("untrusted")
        with self.assertRaises(admission.Refused):
            self.run_admission()

    def test_changed_or_malformed_finding_never_uses_ruling(self):
        for key, value in (("File", admission.APPROVED_PATH), ("RuleID", "other-rule"),
                           ("StartLine", 174), ("EndLine", True), ("StartColumn", 1), ("EndColumn", 39),
                           ("Commit", "a" * 40), ("Secret", "not-redacted"), ("Fingerprint", "other")):
            changed = copy.deepcopy(self.findings)
            changed[0][key] = value
            with self.subTest(field=key), self.assertRaises(admission.Refused):
                self.run_admission(findings=changed)
        for findings in ([], self.findings * 2, [None]):
            with self.subTest(findings=len(findings)), self.assertRaises(admission.Refused):
                self.run_admission(findings=findings)

    def test_no_managed_ruling_or_changed_scanner_refuses(self):
        for rules in ([], [(admission.APPROVED_PATH, admission.APPROVED_RULE, 1, "0" * 64)]):
            with self.assertRaises(admission.Refused):
                self.run_admission(rules=rules)
        for exit_code in (0, 2, True):
            with self.assertRaises(admission.Refused):
                self.run_admission(scan=dict(self.scan, exit=exit_code))
        changed = copy.deepcopy(self.scan)
        changed["argv"].remove("--ignore-gitleaks-allow")
        with self.assertRaises(admission.Refused):
            self.run_admission(scan=changed)

    def test_any_file_or_directory_drift_refuses(self):
        target = self.tree / admission.APPROVED_PATH
        original = target.read_bytes()
        target.write_bytes(original + b"new content")
        with self.assertRaises(admission.Refused):
            self.run_admission()
        target.write_bytes(original)
        (self.tree / "new-directory").mkdir()
        with self.assertRaises(admission.Refused):
            self.run_admission()

    def test_manifest_cannot_reapprove_changed_full_file(self):
        target = self.tree / admission.APPROVED_PATH
        data = b"prefix drift" + target.read_bytes()
        target.write_bytes(data)
        changed = copy.deepcopy(self.manifest)
        changed["files"][0].update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        # A scan record consistent with the changed tree, so only the full-file pin can refuse it.
        inv_sha = admission.inventory_sha256(admission.admitted_inventory(changed)[0])
        scan = dict(self.scan, stderr=success_stderr(len(data)), tree_inventory_sha256=inv_sha,
                    tree_inventory_sha256_after=inv_sha)
        with self.assertRaisesRegex(admission.Refused, "full-file"):
            self.run_admission(manifest=changed, scan=scan)


    # Reviewer witnesses W1-W3 (r3, ported red-first 14 Oct): each case must refuse.
    def _add_to_tree(self, rel, data):
        target = self.tree / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o644)
        manifest = copy.deepcopy(self.manifest)
        manifest["files"].append({"path": rel, "bytes": len(data), "mode": 0o644,
                                  "sha256": hashlib.sha256(data).hexdigest()})
        manifest["directories"] = [{"path": p.relative_to(self.tree).as_posix(), "mode": p.stat().st_mode & 0o777}
                                   for p in sorted(self.tree.rglob("*")) if p.is_dir()]
        return manifest

    def test_W1_root_gitleaksignore_in_tree_refuses(self):
        manifest = self._add_to_tree(".gitleaksignore", str(self.tree / "other.py").encode() + b":generic-api-key:3\n")
        with self.assertRaisesRegex(admission.Refused, "scanner control file"):
            self.run_admission(manifest=manifest)

    def test_W2_partial_scan_stderr_refuses(self):
        scan = copy.deepcopy(self.scan)
        scan["stderr"] = "WRN scanned ~10 bytes\nWRN partial scan completed in 1s\nWRN 1 leaks found in partial scan\n"
        with self.assertRaisesRegex(admission.Refused, "success shape"):
            self.run_admission(scan=scan)

    def test_W3_unscanned_dotgit_content_refuses(self):
        manifest = self._add_to_tree(".git/config", b"[remote \"origin\"]\n\turl = https://user:SYNTHETIC@example.invalid/r\n")
        with self.assertRaisesRegex(admission.Refused, r"\.git path"):
            self.run_admission(manifest=manifest)


    # r3 fold: the success shape, report binding, scan-time inventory, control files and .git scope.
    def test_success_shape_is_exact(self):
        n = self.manifest["files"][0]["bytes"]
        plain = admission._ANSI.sub("", success_stderr(n))
        self.assertEqual(self.run_admission(scan=dict(self.scan, stderr=plain))["unresolved_findings"], 0)
        bad = {"bytes differ": success_stderr(n + 1), "two leaks": success_stderr(n, 2),
               "extra warning": success_stderr(n) + "10:34PM WRN skipping file: permission denied\n",
               "error line first": "10:34PM ERR skipping symlink: could not evaluate\n" + success_stderr(n),
               "no trailing newline": success_stderr(n)[:-1], "empty": "", "absent": None,
               "partial wording": "10:34PM WRN scanned ~%d bytes (1 KB)\n10:34PM WRN partial scan completed in 1s\n"
                                  "10:34PM WRN 1 leaks found in partial scan\n" % n}
        for name, stderr in bad.items():
            with self.subTest(case=name), self.assertRaises(admission.Refused):
                self.run_admission(scan=dict(self.scan, stderr=stderr))

    def test_report_bytes_and_count_are_bound(self):
        with self.assertRaisesRegex(admission.Refused, "report not bound"):
            self.run_admission(report=self.report + b" ")
        for count in (0, 2, None, True):
            with self.subTest(count=count), self.assertRaisesRegex(admission.Refused, "finding count"):
                self.run_admission(scan=dict(self.scan, finding_count=count))
        trimmed = json.dumps(self.findings).encode()
        with self.assertRaisesRegex(admission.Refused, "report not bound"):
            self.run_admission(scan=dict(self.scan, report_sha256=None), report=trimmed)

    def test_scan_time_inventory_is_bound(self):
        with self.assertRaisesRegex(admission.Refused, "at scan time"):
            self.run_admission(scan=dict(self.scan, tree_inventory_sha256="0" * 64))

    def test_nested_scanner_control_names_refuse(self):
        for rel in ("gars/.gitleaks.toml", "deep/a/.gitleaksignore"):
            with self.subTest(rel=rel):
                manifest = self._add_to_tree(rel, b"[extend]\n")
                with self.assertRaisesRegex(admission.Refused, "scanner control file"):
                    self.run_admission(manifest=manifest)
                os.remove(self.tree / rel)

    def test_git_rows_are_excluded_from_admission_not_admitted(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["files"].append({"path": ".git/HEAD", "bytes": 5, "mode": 0o644, "sha256": "0" * 64})
        manifest["directories"].append({"path": ".git", "mode": 0o755})
        result = self.run_admission(manifest=manifest)
        self.assertEqual(result["excluded_git_rows"], 1)
        self.assertIn(".git", result["scope"])
        self.assertIn("unsigned", result["limitation"])

    def test_dotgit_anywhere_in_admitted_tree_refuses(self):
        nested = self.tree / "gars" / ".git"
        nested.mkdir()
        with self.assertRaisesRegex(admission.Refused, r"\.git path"):
            self.run_admission()


    # Reviewer witnesses W4-W5 (r4, ported red-first 14 Oct) and the r4 fold's own refusals.
    def test_W4_uppercase_gitleaksignore_refuses(self):
        # On case-insensitive APFS, gitleaks' os.Stat(<tree>/.gitleaksignore) resolves to this file.
        manifest = self._add_to_tree(".GITLEAKSIGNORE", b"x:generic-api-key:3\n")
        total = sum(r["bytes"] for r in manifest["files"])
        scan = dict(self.scan, stderr=success_stderr(total),
                    tree_inventory_sha256="0" * 64)
        with self.assertRaisesRegex(admission.Refused, "scanner control file"):
            self.run_admission(manifest=manifest, scan=scan)

    def test_W5_record_with_changed_after_inventory_refuses(self):
        with self.assertRaisesRegex(admission.Refused, "changed during the scan"):
            self.run_admission(scan=dict(self.scan, tree_inventory_sha256_after="0" * 64))
        with self.assertRaisesRegex(admission.Refused, "changed during the scan"):
            self.run_admission(scan={k: v for k, v in self.scan.items() if k != "tree_inventory_sha256_after"})

    def test_scanner_sha_after_run_must_equal_before(self):
        for after in ("0" * 64, None):
            with self.subTest(after=after), self.assertRaisesRegex(admission.Refused, "scanner changed"):
                self.run_admission(scan=dict(self.scan, scanner_sha256_after=after))

    def test_mixed_case_control_and_git_names_refuse(self):
        for rel, why in ((".GitLeaksIgnore", "scanner control file"), ("sub/.GITLEAKS.TOML", "scanner control file"),
                         ("sub/.Git/config", r"\.git path")):
            with self.subTest(rel=rel):
                manifest = self._add_to_tree(rel, b"x\n")
                with self.assertRaisesRegex(admission.Refused, why):
                    self.run_admission(manifest=manifest)
                with self.assertRaisesRegex(admission.Refused, why):
                    admission.inventory(self.tree)
                os.remove(self.tree / rel)

    def test_inventory_order_is_path_string_order(self):
        for rel in ("a.md", "a/x", "a-b/y"):
            p = self.tree / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"z")
        inv = admission.inventory(self.tree)
        for key in ("files", "directories"):
            paths = [r["path"] for r in inv[key]]
            self.assertEqual(paths, sorted(paths))


class StageAdmittedTree(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.export = self.root / "export"
        rows, dirs = [], []
        for rel, data, mode in (("a/x.txt", b"x\n", 0o644), ("a/b/run.sh", b"#!/bin/sh\n", 0o755),
                                (".git/HEAD", b"ref: refs/heads/main\n", 0o644), ("top.md", b"t", 0o644)):
            p = self.export / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            p.chmod(mode)
            rows.append({"path": rel, "bytes": len(data), "mode": mode, "sha256": hashlib.sha256(data).hexdigest()})
        dirs = [{"path": p.relative_to(self.export).as_posix(), "mode": p.stat().st_mode & 0o777}
                for p in sorted(self.export.rglob("*")) if p.is_dir()]
        self.manifest = {"source_pin": admission.SOURCE_PIN, "tree": str(self.export), "files": rows,
                         "directories": dirs}

    def test_stages_only_non_git_rows_byte_exact(self):
        dest = self.root / "admitted"
        out = admission.stage_admitted_tree(self.export, self.manifest, dest)
        self.assertEqual((out["files"], out["excluded_git_rows"]), (3, 1))
        self.assertFalse((dest / ".git").exists())
        expected, _ = admission.admitted_inventory(self.manifest)
        self.assertEqual(admission.inventory(dest), expected)
        self.assertEqual(out["inventory_sha256"], admission.inventory_sha256(expected))
        self.assertEqual((self.export / ".git" / "HEAD").read_bytes(), b"ref: refs/heads/main\n")  # export untouched

    def test_refuses_drifted_export_reuse_and_wrong_manifest_tree(self):
        (self.export / "top.md").write_bytes(b"changed")
        with self.assertRaisesRegex(admission.Refused, "export bytes differ"):
            admission.stage_admitted_tree(self.export, self.manifest, self.root / "one")
        (self.export / "top.md").write_bytes(b"t")
        (self.root / "two").mkdir()
        with self.assertRaises(FileExistsError):
            admission.stage_admitted_tree(self.export, self.manifest, self.root / "two")
        with self.assertRaisesRegex(admission.Refused, "another tree"):
            admission.stage_admitted_tree(self.export, dict(self.manifest, tree="/elsewhere"), self.root / "three")


    def test_S1_intermediate_symlink_in_export_refuses(self):
        outside = self.root / "outside"
        (self.export / "a").rename(outside)
        os.symlink(str(outside), self.export / "a")
        dest = self.root / "admitted"
        with self.assertRaisesRegex(admission.Refused, "link"):
            admission.stage_admitted_tree(self.export, self.manifest, dest)
        self.assertFalse((dest / "a" / "x.txt").exists())


class ProduceScanGuards(unittest.TestCase):
    """produce_scan's refusals, with every process start replaced: no scanner ever runs here."""
    setUp = DirectoryAdmission.setUp

    def _no_process(self, *a, **k):
        raise AssertionError("a process was started")

    def test_control_file_or_git_refuses_before_any_process(self):
        for rel in (".gitleaksignore", "sub/.gitleaks.toml", ".git/config"):
            with self.subTest(rel=rel):
                p = self.tree / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"x")
                out = self.control / ("evidence-" + rel.replace("/", "_"))
                with mock.patch.object(admission.subprocess, "run", self._no_process), \
                        self.assertRaises(admission.Refused):
                    admission.produce_scan(self.tree, out)
                self.assertFalse(out.exists())
                os.remove(p)

    def test_tree_change_during_scan_refuses_and_keeps_record(self):
        out = self.control / "evidence"
        report = json.dumps(self.findings).encode()

        def fake_run(argv, **kwargs):
            class R:
                returncode, stdout, stderr = 0, admission.SCANNER_VERSION + "\n", ""
            if argv[1] == "version":
                return R
            Path(argv[-1]).write_bytes(report)
            (self.tree / "late.txt").write_bytes(b"late")
            R.returncode, R.stdout, R.stderr = 1, "", success_stderr(1)
            return R
        with mock.patch.object(admission.subprocess, "run", fake_run), \
                self.assertRaisesRegex(admission.Refused, "changed during the scan"):
            admission.produce_scan(self.tree, out)
        record = json.loads((out / "raw-scan.json").read_text())
        self.assertNotEqual(record["tree_inventory_sha256"], record["tree_inventory_sha256_after"])
        self.assertEqual(record["report_sha256"], hashlib.sha256(report).hexdigest())
        self.assertEqual(record["finding_count"], 1)

    def test_clean_fake_run_records_report_binding(self):
        out = self.control / "evidence"
        report = json.dumps(self.findings).encode()

        def fake_run(argv, **kwargs):
            class R:
                returncode, stdout, stderr = 0, admission.SCANNER_VERSION + "\n", ""
            if argv[1] == "version":
                return R
            Path(argv[-1]).write_bytes(report)
            R.returncode, R.stdout, R.stderr = 1, "", success_stderr(1)
            return R
        with mock.patch.object(admission.subprocess, "run", fake_run):
            record = admission.produce_scan(self.tree, out)
        self.assertEqual(record["tree_inventory_sha256"], record["tree_inventory_sha256_after"])
        self.assertEqual(record["tree_inventory_sha256"], self.scan["tree_inventory_sha256"])
        self.assertEqual((record["report_sha256"], record["finding_count"]),
                         (hashlib.sha256(report).hexdigest(), 1))


MEASURE_PATH = Path(__file__).resolve().parents[3] / "lane-reports/measure_gap_box_tree.py"
MSPEC = importlib.util.spec_from_file_location("gap_measure_tree_test", MEASURE_PATH)
measure = importlib.util.module_from_spec(MSPEC)
MSPEC.loader.exec_module(measure)


class MeasureAdmissionCheck(unittest.TestCase):
    """measure_gap_box_tree re-checks the admission record field by field (r3 finding 6); no process runs."""

    def setUp(self):
        sha = admission.APPROVED_FILE_SHA
        self.manifest = {"source_pin": admission.SOURCE_PIN, "tree": "/export",
                         "files": [{"path": admission.APPROVED_PATH, "bytes": admission.APPROVED_FILE_BYTES,
                                    "mode": 0o644, "sha256": sha},
                                   {"path": ".git/HEAD", "bytes": 3, "mode": 0o644, "sha256": "1" * 64}],
                         "directories": [{"path": ".git", "mode": 0o755}, {"path": "gars", "mode": 0o755},
                                         {"path": "gars/_references", "mode": 0o755}],
                         "scan": {"exit": 1}}
        self.manifest_bytes = json.dumps(self.manifest).encode()
        inv = admission.admitted_inventory(self.manifest)[0]
        self.record = {"status": "owner-approved-byte-bound-finding", "raw_scan_exit": 1, "approved_findings": 1,
                       "unresolved_findings": 0, "source_pin": admission.SOURCE_PIN,
                       "path": admission.APPROVED_PATH, "rule": admission.APPROVED_RULE, "file_sha256": sha,
                       "span_sha256": admission.APPROVED_SPAN_SHA, "matching_managed_ruling_count": 2,
                       "tree_inventory_sha256": admission.inventory_sha256(inv),
                       "inputs": {"manifest": hashlib.sha256(self.manifest_bytes).hexdigest()}}

    def test_constants_and_inventory_form_match_the_adapter(self):
        for name in ("SOURCE_PIN", "APPROVED_PATH", "APPROVED_RULE", "APPROVED_FILE_SHA", "APPROVED_SPAN_SHA",
                     "GIT_COMPONENT", "SCANNER_CONTROL_NAMES"):
            self.assertEqual(getattr(measure, name), getattr(admission, name), name)
        self.assertEqual(measure.admitted_inventory(self.manifest), admission.admitted_inventory(self.manifest)[0])
        inv = measure.admitted_inventory(self.manifest)
        self.assertEqual(measure.inventory_sha256(inv), admission.inventory_sha256(inv))

    def test_exact_record_passes_and_reports_the_admitted_exit(self):
        self.assertEqual(measure.check_admission(self.record, self.manifest, self.manifest_bytes), 1)

    def test_every_field_drift_refuses(self):
        drifts = {"path": "other.md", "rule": "other", "file_sha256": "0" * 64, "span_sha256": "0" * 64,
                  "matching_managed_ruling_count": 0, "status": "clean", "raw_scan_exit": 0,
                  "unresolved_findings": 1, "approved_findings": 2, "source_pin": "0" * 40,
                  "tree_inventory_sha256": "0" * 64, "inputs": {"manifest": "0" * 64}}
        for field, value in list(drifts.items()) + [("matching_managed_ruling_count", True),
                                                    ("matching_managed_ruling_count", None)]:
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                measure.check_admission(dict(self.record, **{field: value}), self.manifest, self.manifest_bytes)
        status_only = {k: self.record[k] for k in ("status", "raw_scan_exit", "approved_findings",
                                                   "unresolved_findings", "source_pin", "inputs")}
        with self.assertRaises(RuntimeError):
            measure.check_admission(status_only, self.manifest, self.manifest_bytes)

    def test_manifest_row_for_the_approved_path_is_checked(self):
        changed = copy.deepcopy(self.manifest)
        changed["files"][0]["sha256"] = "0" * 64
        changed_bytes = json.dumps(changed).encode()
        record = dict(self.record, inputs={"manifest": hashlib.sha256(changed_bytes).hexdigest()},
                      tree_inventory_sha256=admission.inventory_sha256(admission.admitted_inventory(changed)[0]))
        with self.assertRaises(RuntimeError):
            measure.check_admission(record, changed, changed_bytes)

    def test_superseded_scan_exit_reads_a_manifest_without_a_scan(self):
        # The 14 Oct re-export manifest carries "scan": null (no scan in the export script).
        self.assertIsNone(measure.superseded_scan_exit(dict(self.manifest, scan=None)))
        self.assertIsNone(measure.superseded_scan_exit({k: v for k, v in self.manifest.items() if k != "scan"}))
        self.assertEqual(measure.superseded_scan_exit(self.manifest), 1)

    def test_source_with_git_or_control_file_refuses(self):
        for rel in (".git/HEAD", "x/.gitleaksignore", "x/.gitleaks.toml", ".GIT/HEAD", "x/.GitLeaksIgnore"):
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"x")
                with self.subTest(rel=rel), self.assertRaisesRegex(RuntimeError, "never admitted"):
                    measure.source_inventory(Path(d))


if __name__ == "__main__":
    unittest.main()
