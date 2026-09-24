#!/usr/bin/env python3
"""Disposable, byte-restored faults; never mutate the source checkout."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
STAGE = 'gars/_system/stage01_samplesheet.py'
INTEGRITY = 'gars/_system/integrity.py'
DE = 'gars/_system/wrappers/rnaseq-de/rnaseq_de.py'
EVIDENCE = 'gars/_system/claims/evidence_check.py'
EMIT = 'gars/_system/claims/emit_report.py'
DOI = 'gars/_system/resolve_citation.py'
RUNNER = 'tests/test_planted_defects.py'
DESIGN_TEST = 'DevelopmentCatalogueTests.'
SEALED_TEST = 'SealedOutputDisciplineTests.'
CITATION_TEST = 'CitationResolutionTests.'
REPORT_TEST = 'EmitReportTests.'
FAULTS = [
    ('sex confounding removed', STAGE, 'if confounded:', 'if False and confounded:', RUNNER, DESIGN_TEST + 'test_sex_age_thresholds'),
    ('imbalance threshold 0.9', STAGE, 'SEX_PROPORTION_THRESHOLD = 0.5', 'SEX_PROPORTION_THRESHOLD = 0.9', RUNNER, DESIGN_TEST + 'test_sex_age_thresholds'),
    ('cell pseudoreplication removed', STAGE, 'if "cell_barcode" in samples["fields"]:', 'if False and "cell_barcode" in samples["fields"]:', RUNNER, DESIGN_TEST + 'test_development_exit'),
    ('subject count removed', STAGE, 'if unit:', 'if False and unit:', RUNNER, DESIGN_TEST + 'test_subject_replication'),
    ('index comparison inverted', STAGE, 'indexes.most_common(1)[0][0] != sample.get("library_index")', 'indexes.most_common(1)[0][0] == sample.get("library_index")', RUNNER, DESIGN_TEST + 'test_case_whitespace_lanes_and_order'),
    ('not_checkable counted pass', STAGE, '"outcome": "not_checkable"', '"outcome": "pass"', RUNNER, DESIGN_TEST + 'test_not_checkable_is_not_pass'),
    ('evidence hash not compared', EVIDENCE, "if digest.hexdigest() != artifact['sha256']:", "if False and digest.hexdigest() != artifact['sha256']:", 'gars/tests/test_emit_report.py', REPORT_TEST + 'test_changed_hash'),
    ('absolute evidence accepted', EVIDENCE, 'if relative.is_absolute() or pardir in relative.parts:', 'if pardir in relative.parts:', 'gars/tests/test_emit_report.py', REPORT_TEST + 'test_path_containment'),
    ('padj below pvalue allowed', DE, 'not 0 <= p <= q <= 1', 'not (0 <= p <= 1 and 0 <= q <= 1)', RUNNER, DESIGN_TEST + 'test_collect_diagnostic_drift'),
    ('BH recompute removed', DE, 'if abs(q - corrected) > BH_RELATIVE_TOLERANCE * abs(corrected):', 'if False and abs(q - corrected) > BH_RELATIVE_TOLERANCE * abs(corrected):', RUNNER, DESIGN_TEST + 'test_collect_diagnostic_drift'),
    ('Crossref 404 alone unresolved', DOI, "if status != 404:", "if status == 404:\n            return 'citation_unresolved'\n        if status != 404:", 'gars/tests/test_citation_resolution.py', CITATION_TEST + 'test_prefixes_and_datacite_fallback'),
    ('network error resolved', DOI, "        return 'citation_unverifiable'\n\n\ndef main", "        return 'resolved'\n\n\ndef main", 'gars/tests/test_citation_resolution.py', CITATION_TEST + 'test_transient_refuses'),
    ('unparseable plant skipped', RUNNER, "except BaseException:\n                totals['errors'] += 1", "except BaseException:\n                totals['graded'] -= 1\n                totals['errors'] += 1", RUNNER, SEALED_TEST + 'test_sentinel_and_error_accounting'),
    ('unmapped folded into class', RUNNER, "totals['unmapped'] += 1", "totals['unmapped'] += 1\n                        counts[2][0] += 1\n                        counts[2][1] += 1", RUNNER, SEALED_TEST + 'test_unmapped_outside_arithmetic'),
    ('Hi-C denominator removed', RUNNER, 'counts[10] = [0, 1]', 'counts[10] = [0, 0]', RUNNER, SEALED_TEST + 'test_sentinel_and_error_accounting'),
    ('truncated plain FASTQ passes', INTEGRITY, 'if mode == "skip" or (mode == "quick" and not str(path).endswith(".gz")):', 'if mode == "skip" or not str(path).endswith(".gz"):', 'gars/tests/test_integrity_records.py', 'IntegrityRecordTests.test_stage01_plain_truncation_and_default'),
    ('gzip-valid record truncation passes', INTEGRITY, 'if is_fastq:', 'if is_fastq and not str(path).endswith(".gz"):', 'gars/tests/test_integrity_records.py', 'IntegrityRecordTests.test_records_plain_and_gzip'),
    ('report written before preflight', EMIT, '        code = evidence_check.main', '        args.out.write_text("premature report")\n        code = evidence_check.main', 'gars/tests/test_emit_report.py', REPORT_TEST + 'test_missing_path'),
    ('sealed stdout leaked', RUNNER, 'with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):', 'with contextlib.ExitStack():', RUNNER, SEALED_TEST + 'test_sentinel_and_error_accounting'),
    ('invalid_design mapped without family', RUNNER, "if reason == 'invalid_design' and expected.get('detail_contains') in GROUP_ONE_FAMILY:", "if reason == 'invalid_design':", RUNNER, DESIGN_TEST + 'test_row1_mapping_detail_family'),
    ('BH tolerance 1e-6', DE, 'BH_RELATIVE_TOLERANCE = 1e-4', 'BH_RELATIVE_TOLERANCE = 1e-6', RUNNER, DESIGN_TEST + 'test_collect_diagnostic_drift'),
    ('environment replay switch', 'gars/_system/resolve_citation.py', '    transport = transport or live_transport', '    import os\n    if os.getenv("GARS_REPLAY"):\n        with open(os.getenv("GARS_REPLAY")) as handle:\n            recorded = json.load(handle)["responses"]\n        def recorded_transport(url):\n            row = next(r for r in recorded if r["request_url"] == url)\n            return row["status"], row["body"].encode("utf-8")\n        transport = recorded_transport\n    transport = transport or live_transport', 'gars/tests/test_citation_resolution.py', 'CitationResolutionTests.test_no_replay_switch'),
    ('suppressed replay option', DOI, "result.add_argument('reference')", "result.add_argument('reference')\n    result.add_argument('--replay', help=argparse.SUPPRESS)", 'gars/tests/test_citation_resolution.py', CITATION_TEST + 'test_no_replay_switch'),
    ('renderer receives from-db', EMIT, "'--snapshot', str(snapshot), '--manifest', str(args.manifest)", "'--from-db', args.from_db or '1', '--manifest', str(args.manifest)", 'gars/tests/test_emit_report.py', REPORT_TEST + 'test_database_export_once_same_snapshot'),
]


def main():
    outcomes = []
    with tempfile.TemporaryDirectory(prefix='defect-faults-') as folder:
        twin = Path(folder)
        for relative in ('gars/_system', 'gars/_references', 'gars/_templates', 'gars/tests',
                         'benchmarks/defects'):
            shutil.copytree(str(REPO / relative), str(twin / relative),
                            ignore=shutil.ignore_patterns('__pycache__'))
        (twin / 'tests').mkdir()
        for relative in (RUNNER, 'tests/run_tests.py'):
            shutil.copy2(str(REPO / relative), str(twin / relative))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        for name, relative, old, new, test, method in FAULTS:
            target = twin / relative
            backup = target.read_bytes()
            source = backup.decode()
            if source.count(old) != 1:
                raise ValueError('mutation target not unique: ' + name)
            try:
                mutant = source.replace(old, new)
                ast.parse(mutant)
                target.write_text(mutant)
                result = subprocess.run([sys.executable, str(twin / test), method],
                                        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        universal_newlines=True, timeout=120)
                red = result.returncode != 0 and 'FAILED (' in result.stdout
                outcomes.append(dict(fault=name, test=test + ' ' + method, red=red))
                print('%s: %s' % ('RED' if red else 'SURVIVED', name), flush=True)
                if not red:
                    print(result.stdout)
            finally:
                target.write_bytes(backup)
                if target.read_bytes() != backup:
                    raise AssertionError('restore failed')
    print('red-on-fault: %d/%d' % (sum(o['red'] for o in outcomes), len(outcomes)))
    return 0 if all(o['red'] for o in outcomes) else 1


if __name__ == '__main__':
    sys.exit(main())
