#!/usr/bin/env python3
"""The rules scanner scan_record.scan takes as `rules_scanner` (CP2; glitch-06's ruling, 14 Oct 2026): gitleaks'
default rules over each of a take's files, on athena, at the pinned version.

    gitleaks_scanner(runtime, report_dir, *, binary=GITLEAKS_PATH, caller_env=None) -> scan(paths)
    scan(paths) -> [{"path", "line", "rule"}]

The adapter was reviewed as the stub-take candidate (stub-take review: ACCEPT) and proven on athena: a clean record
set passes, and a GitHub-token-shaped fake is refused by rule `github-pat` (lane-reports/stub-take-20261014,
stub-take-run1..4.json). Each path is scanned alone, `gitleaks dir <file> --no-banner --redact --report-format json
--report-path <report> --exit-code 0`: the report never holds a finding's value (--redact), only its line and rule.

FAILING CLOSED. The scanner is built only when the binary's sha256 is the pin and `gitleaks version` prints the pinned
version; a scanner exit other than 0, a missing or unparsable report, or a finding off its shape raises ScannerRefused,
so scan_record never reads a failed scan as clean. It is pointed at a take's own files only, never a folder that holds
the Brain or a whole workspace. Standard library only (plus run_take's runtime protocol).
"""

from __future__ import annotations

import hashlib
import json
import os

from box import run_take

# The pin (box lane, 14 Oct 2026; athena's acquisition record ~/gap4-tools/gitleaks-8.30.1/acquisition.json: the
# official v8.30.1 linux x64 release, archive sha256 551f6fc8..., binary sha256 below; measured again in every stub take).
GITLEAKS_VERSION = "8.30.1"
GITLEAKS_SHA256 = "88f91962aa2f93ac6ab281d553b9e125f5197bbbce38f9f2437f7299c32e5509"
GITLEAKS_PATH = "/home/javier/gap4-tools/gitleaks-8.30.1/gitleaks"
SCAN_TIMEOUT_S = 120
REPORT_FIELDS = {"line": "StartLine", "rule": "RuleID"}


class ScannerRefused(RuntimeError):
    """The scanner is not the pinned one, or a scan did not complete: never read as clean."""


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_argv(binary: str, path: str, report: str) -> list:
    return [binary, "dir", path, "--no-banner", "--redact", "--report-format", "json", "--report-path", report,
            "--exit-code", "0", "--log-level", "warn"]


def gitleaks_scanner(runtime, report_dir: str, *, binary: str = GITLEAKS_PATH, caller_env=None):
    """The pinned gitleaks, checked by sha256 and by its version line, as scan_record's rules_scanner."""
    binary = run_take._abs_path(binary, "the gitleaks binary")
    report_dir = run_take._abs_path(report_dir, "report_dir")
    if os.path.islink(binary) or not os.path.isfile(binary):
        raise ScannerRefused("the gitleaks binary is not a regular file")
    if _sha256_file(binary) != GITLEAKS_SHA256:
        raise ScannerRefused("the gitleaks binary is not the pinned one (sha256)")
    if os.path.islink(report_dir) or not os.path.isdir(report_dir) or os.listdir(report_dir):
        raise ScannerRefused("the report folder must exist and be empty")
    env = run_take.runtime_env(caller_env)
    v = runtime.run([binary, "version"], env=env, timeout=SCAN_TIMEOUT_S)
    if v.returncode != 0 or v.stdout.strip() != GITLEAKS_VERSION:
        raise ScannerRefused(f"gitleaks does not report version {GITLEAKS_VERSION}")
    counter = [0]

    def scan(paths):
        out = []
        for p in paths:
            p = run_take._abs_path(p, "a scanned path")
            counter[0] += 1
            report = os.path.join(report_dir, f"gitleaks-{counter[0]}.json")
            try:
                c = runtime.run(scan_argv(binary, p, report), env=env, timeout=SCAN_TIMEOUT_S)
            except TimeoutError:
                raise ScannerRefused(f"gitleaks timed out on {p}") from None
            if c.returncode != 0:
                raise ScannerRefused(f"gitleaks exited {c.returncode} on {p}")
            try:
                with open(report, encoding="utf-8") as fh:
                    findings = json.load(fh)
            except (OSError, ValueError):
                raise ScannerRefused(f"gitleaks wrote no readable report for {p}") from None
            if findings is None:
                findings = []
            if not isinstance(findings, list):
                raise ScannerRefused(f"gitleaks' report for {p} is not a list")
            for f in findings:
                line, rule = (f.get(REPORT_FIELDS[k]) if isinstance(f, dict) else None for k in ("line", "rule"))
                if not (isinstance(line, int) and not isinstance(line, bool) and line >= 1 and isinstance(rule, str)
                        and rule):
                    raise ScannerRefused(f"a gitleaks finding for {p} is off its shape")
                out.append({"path": p, "line": line, "rule": rule})
        return out
    return scan
