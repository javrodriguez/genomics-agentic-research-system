#!/usr/bin/env python3
"""Producer-authored development catalogue and content-silent sealed interface.

**The sealed interface (fixed here so the seal can run beside the build).**
`GARS_SEALED_DEFECT_FIXTURES` names a directory holding one subdirectory per plant, named `p01`, `p02`, … (never a descriptive name; review MINOR-4), each with one of three layouts:
- (a) a complete stage-00 project for classes 3–6: `00_data/<assay>/{samples.csv,files.csv,raw/}` and `_config/<assay>.yaml`, exactly as row 1's sealed interface, with the columns of "The schema the detectors read";
- (b) for class 8, `de_results.csv` (the schema `gene,baseMean,log2FoldChange,pvalue,padj`), which the runner places into its own scaffold and grades through the real `collect`;
- (c) for classes 7 and 9, `snapshot.json` in row 7's `claims_export` shape plus a `project/` tree, graded through `emit_report.py`.
- A plant with `class_id: 0` is a sealed **clean** project in layout (a), expected to raise no flag.

Every plant carries `expected.json`: `{"class_id": <0-10>, "expected_flag": "<flag or none>", "expected_stage": "<stage>", "seal_type": "independent_context" | "external_human_seal", "canary": "<32 hex characters>"}`.
The `canary` is a random token the sealer also writes into one data cell the plant's layout carries, where no detector reads it (review NOTE-A): an extra `samples.csv` column named `plant_note` in layout (a) (the open schema, 0043, allows it, and no detector reads that column; never in a sample id, which stage 00 derives from file names); an extra trailing column `plant_note` in `de_results.csv` for layout (b) (the collect gate reads columns by name; Brief A's clean projects include one table with that extra column, proving it changes no verdict); a claim's `text` in `snapshot.json` for layout (c). The runner never prints it; `seal_ops.py complete` copies it once into the manifest, and every later leak count reads the manifest (below).

The runner routes by `class_id`, grades through the stage entry point, and counts a catch only when the named flag appears there.
Output discipline (review MINOR-4), enforced by a test:
- each plant runs in a `try/except`, with the entry point's stdout and stderr captured and discarded;
- a plant that raises is counted `error` (graded, not caught), never skipped;
- it prints only `sealed <id>: <caught>/<planted>` per class, `sealed clean: <flagged>/<n>`, the seal-type counts, `sealed graded <g> of <s> plants seen`, and `row 1 mapped: <m>` / `row 1 unmapped: <u>`;
- a test builds a synthetic sealed folder whose sample ids, file names, folder names and `expected.json` extras all carry a sentinel string, runs the sealed class, and asserts the sentinel appears 0 times in the captured output.

It also accepts row 1's `GARS_SEALED_DESIGN_FIXTURES` (`tests/test_stage01_design.py:8-16` interface), mapping through a committed map that keeps row 1's own `detail_contains` requirement (review MAJOR-5):
- `confounded_condition` → class 1;
- `insufficient_biological_replicates` → class 2;
- `invalid_design` → class 2 **only** when `detail_contains` falls in the group-of-one message family (the runner matches `detail_contains` against the committed family, the literal fragments of the stage 01 messages at `:588-590` and the ATAC floor; for example "cannot be tested for differential expression");
- anything else → `unmapped`: printed on its own line, never counted as caught, and kept out of the catalogue arithmetic, because it is one of row 1's §7.2 checks outside §11.2's ten classes.
A mapped plant is caught only when the stage 01 CLI's failure carries both the reason and `detail_contains`, exactly as `SealedDesignTests` grades it.

**The schema the detectors read (review MAJOR-2).**
It is a contract, not detector rule text.
The same block is copied verbatim into the sealed interface, into `benchmarks/defects/SEALED-INTERFACE.md`, and into the stage 00/01 contracts (`gars/00_initialize_project/CONTEXT.md`, `gars/01_prepare_samplesheets/CONTEXT.md`), so a sealer and a user read the same words.
All columns are optional `samples.csv` columns under the open schema (decision 0043); no config key is added (review MAJOR-9).
- `subject`: the independent biological unit (donor, patient, animal); rows sharing a value are not independent replicates.
- `biological_unit`: a synonym of `subject` kept for row 2's fixtures; when both are present, `subject` wins.
- `cell_barcode`: present only when each row is a single cell (or a cell-level sub-sample); its presence marks the design as cell-level.
- `library_index`: the library's i7 index sequence, or `i7+i5` for dual indexing, in the exact form the CASAVA 1.8 FASTQ header carries after the last `:` (for example `ACGTACGT` or `ACGTACGT+TTGACCAA`); never a library name.
- `sex`: one of `F`, `M`, `unknown` (case-sensitive).
- `age`: age in years, a non-negative number; blank means unknown.
"""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'gars/tests'))
from support import module
from test_citation_resolution import replay

CATALOGUE = json.loads((REPO / 'benchmarks/defects/catalogue.yaml').read_text())
generate = module(REPO / 'benchmarks/defects/generate.py', 'defect_generate')
emitter = module(REPO / 'gars/_system/claims/emit_report.py', 'defect_emitter')
legacy = module(REPO / 'tests/run_tests.py', 'defect_legacy')
STAGE = REPO / 'gars/_system/stage01_samplesheet.py'
DE = REPO / 'gars/_system/wrappers/rnaseq-de/rnaseq_de.py'
GROUP_ONE_FAMILY = ('of one cannot be tested for differential expression',
                    'cannot be tested for differential expression',
                    'at least 2 per level required')
FLAGS = {entry['id']: entry['expected_flag'] for entry in CATALOGUE['entries']}
STAGES = {entry['id']: entry['expected_stage'] for entry in CATALOGUE['entries']}


def cli(script, args):
    proc = subprocess.run([sys.executable, str(script)] + [str(a) for a in args],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=120)
    return proc.returncode, json.loads(proc.stdout)


def stage(project):
    return cli(STAGE, ['--project', project, '--check', '--verify-integrity', 'full'])


def collect(table):
    """Every call builds a new real prepare/submit-evidence/collect scaffold."""
    with tempfile.TemporaryDirectory(prefix='defect-collect-') as folder:
        project = Path(folder)
        (project / '_config').mkdir()
        (project / '_config/rnaseq_bulk.yaml').write_text(
            'de:\n  formula: "' + chr(126) + ' condition"\n  contrast: "condition,A,B"\n'
            'compute:\n  partition: fixture\n  time: "1:00:00"\n  cpus: 1\n'
            '  mem: 1G\n  work_dir: ' + str(project / 'work') + '\n')
        (project / '01_samplesheets').mkdir()
        design = project / '01_samplesheets/rnaseq_bulk_design.csv'
        design.write_text('sample_id,condition,group,replicate\nS1,A,A,1\nS2,A,A,2\nS3,B,B,1\nS4,B,B,2\n')
        counts = project / 'counts.tsv'
        counts.write_text('gene_id\tgene_name\tS1\tS2\tS3\tS4\ng1\tG1\t10\t11\t12\t13\n')
        code, result = cli(DE, ['prepare', '--project', project, '--counts', counts, '--design', design])
        if code:
            raise ValueError('scaffold prepare refused')
        substage = project / '02_bioinformatics/rnaseq_bulk/02_rnaseq-de'
        run = substage / 'run'
        (run / 'tables').mkdir(parents=True, exist_ok=True)
        (run / 'figures').mkdir(exist_ok=True)
        (substage / 'adapted').mkdir(exist_ok=True)
        (run / 'tables/de_results.csv').write_bytes(Path(table).read_bytes())
        (run / 'tables/normalized_counts.csv').write_text('gene,S1,S2,S3,S4\ng1,1,2,3,4\n')
        for name in ('pca.png', 'volcano.png', 'ma_plot.png'):
            (run / 'figures' / name).write_text('fixture image')
        (run / 'report.md').write_text('Synthetic report\n')
        (run / '.gars_run_complete').write_text('complete\n')
        (substage / 'adapted/counts_gene.tsv').write_text('gene\tS1\ng1\t1\n')
        (substage / 'adapted/gene_id_to_name.tsv').write_text('gene_id\tgene_name\ng1\tG1\n')
        legacy.completed_fixture_submission(project, substage)
        return cli(DE, ['collect', '--project', project])


def emission(project, transport=replay):
    with tempfile.TemporaryDirectory(prefix='defect-report-') as folder:
        out = Path(folder) / 'report.md'
        manifest = project / 'manifest.json'
        if not manifest.is_file():
            manifest = Path(folder) / 'manifest.json'
            manifest.write_text('{}\n')
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = emitter.main(['--snapshot', str(project / 'snapshot.json'),
                                 '--manifest', str(manifest), '--project', str(project / 'project'),
                                 '--out', str(out)], transport=transport)
        return code, output.getvalue(), out.exists()


def grade(project, cid, flag, detail='', transport=replay):
    if cid == 10:
        return False
    if cid in (7, 9):
        code, output, written = emission(project, transport=transport)
        return code != 0 and not written and flag in {line.split(':', 1)[0] for line in output.splitlines()}
    if cid == 8:
        code, result = collect(project / 'de_results.csv')
        failures = result.get('failures', [])
    else:
        code, result = stage(project)
        assays = result.get('assays', {}).values()
        failures = [f for assay in assays for f in assay.get('failures', [])]
        if flag == 'covariate_imbalance':
            return any(f.get('check') == flag and f.get('disposition') == 'DEGRADE'
                       and detail in f.get('detail', '')
                       for assay in assays for f in assay.get('design_check', {}).get('flags', []))
    return code == 1 and result.get('ok') is False and any(
        f.get('check') == flag and detail in f.get('detail', '')
        and (cid != 2 or flag != 'invalid_design' or any(
            fragment in f.get('detail', '')
            for fragment in CATALOGUE['entries'][1]['detail_contains']['invalid_design']))
        and (cid != 3 or flag != 'confounded_condition'
             or re.search(r'\bsex\b', f.get('detail', '')) is not None)
        for f in failures)


def clean(project, all_stages=False):
    code, result = stage(project)
    flagged = code != 0 or result.get('ok') is not True or any(
        assay.get('failures') or assay.get('design_check', {}).get('flags')
        for assay in result.get('assays', {}).values())
    if all_stages:
        de_code, _ = collect(project / 'de_results.csv')
        report_code, _, written = emission(project)
        flagged = flagged or de_code != 0 or report_code != 0 or not written
    return not flagged


def row1_class(expected):
    reason = expected.get('reason')
    if reason == 'confounded_condition':
        return 1
    if reason == 'insufficient_biological_replicates':
        return 2
    if reason == 'invalid_design' and expected.get('detail_contains') in GROUP_ONE_FAMILY:
        return 2
    return None


def sealed_measure(root, row1=None):
    """Never propagate input content, diagnostics or exceptions into output."""
    counts = {i: [0, 0] for i in range(1, 11)}
    counts[10] = [0, 1]
    totals = dict(seen=0, graded=0, errors=0, clean=0, flagged=0, mapped=0, unmapped=0,
                  independent_context=0, external_human_seal=0, verdicts=[])
    try:
        plants = [(p, False) for p in sorted(Path(root).iterdir()) if p.is_dir()]
        if row1:
            plants += [(p, True) for p in sorted(Path(row1).iterdir()) if p.is_dir()]
    except Exception:
        plants = []
        totals['errors'] += 1
    if not plants:
        totals['errors'] += 1
    for plant, old in plants:
        totals['seen'] += 1
        cid = None
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                expected = json.loads((plant / 'expected.json').read_text())
                seal = expected['seal_type']
                if seal not in ('independent_context', 'external_human_seal'):
                    raise ValueError('seal')
                totals[seal] += 1
                if old:
                    if not isinstance(expected.get('detail_contains'), str) or not expected['detail_contains']:
                        raise ValueError('detail')
                    cid = row1_class(expected)
                    if cid is None:
                        totals['unmapped'] += 1
                        totals['verdicts'].append((None, 'unmapped'))
                        continue
                    totals['mapped'] += 1
                    flag, detail = expected['reason'], expected['detail_contains']
                else:
                    cid = expected['class_id']
                    if type(cid) is not int or cid not in range(11):
                        raise ValueError('class')
                    if not re.fullmatch('[0-9a-fA-F]{32}', expected['canary']):
                        raise ValueError('canary')
                    flag, detail = expected['expected_flag'], ''
                    if cid == 0:
                        if flag != 'none' or expected['expected_stage'] != '01_prepare_samplesheets':
                            raise ValueError('clean declaration')
                        totals['clean'] += 1
                        flagged = not clean(plant)
                        totals['flagged'] += int(flagged)
                        totals['verdicts'].append((0, 'flagged' if flagged else 'clean'))
                        continue
                    if flag not in FLAGS[cid] or expected['expected_stage'] != STAGES[cid]:
                        raise ValueError('expectation')
                counts[cid][1] += 1
                # Sealed class 9 uses live lookup on the measurement host, never
                # development replay; default tests stub the live transport in process.
                caught = grade(plant, cid, flag, detail, None if cid == 9 else replay)
                counts[cid][0] += int(caught)
                totals['verdicts'].append((cid, 'caught' if caught else 'not_caught'))
            except BaseException:
                totals['errors'] += 1
                error_class = cid if type(cid) is int and cid in range(11) else None
                totals['verdicts'].append((error_class, 'error'))
    totals['graded'] = len(totals['verdicts'])
    for cid, (caught, planted) in sorted(counts.items()):
        print('sealed %d: %d/%d' % (cid, caught, planted))
    caught = sum(planted > 0 and got == planted for got, planted in counts.values())
    print('planted-defects sealed: %d/10 classes (placeholder 10 counted planted, not caught)' % caught)
    print('sealed clean: %d/%d' % (totals['flagged'], totals['clean']))
    print('sealed independent_context: %d' % totals['independent_context'])
    print('sealed external_human_seal: %d' % totals['external_human_seal'])
    print('sealed graded %d of %d plants seen' % (totals['graded'], totals['seen']))
    print('row 1 mapped: %d' % totals['mapped'])
    print('row 1 unmapped: %d' % totals['unmapped'])
    return caught, counts, totals


class DevelopmentCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='defect-dev-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        generate.generate(self.root)

    def test_catalogue_table_and_pins(self):
        expected = [
            (1, 'batch fully confounded with condition', ['confounded_condition'], '01_prepare_samplesheets', 'active'),
            (2, 'n = 1 per group', ['insufficient_biological_replicates', 'invalid_design'], '01_prepare_samplesheets', 'active'),
            (3, 'sex/age imbalance across arms', ['confounded_condition', 'covariate_imbalance'], '01_prepare_samplesheets', 'active'),
            (4, 'cells treated as replicates', ['pseudoreplication'], '01_prepare_samplesheets', 'active'),
            (5, 'sample labels swapped between `samples.csv` and FASTQ', ['sample_label_mismatch'], '01_prepare_samplesheets', 'active'),
            (6, 'truncated FASTQ', ['integrity'], '01_prepare_samplesheets', 'active'),
            (7, 'fabricated output path in a finding', ['evidence_missing', 'evidence_hash_mismatch'], 'report_emit', 'active'),
            (8, 'DE table with raw p-values, no correction', ['uncorrected_pvalues'], '02_collect', 'active'),
            (9, 'claim citing a non-existent DOI', ['citation_unresolved'], 'report_emit', 'active'),
            (10, 'Hi-C resolution mismatch (placeholder)', [], None, 'placeholder')]
        self.assertEqual([tuple(e[k] for k in ('id', 'class', 'expected_flag', 'expected_stage', 'status'))
                          for e in CATALOGUE['entries']], expected)
        self.assertNotIn('plant_recipe', CATALOGUE['entries'][-1])
        self.assertNotIn('fixture', CATALOGUE['entries'][-1])
        for relative, digest in CATALOGUE['sha256'].items():
            committed = REPO / 'benchmarks/defects' / relative
            regenerated = self.root / Path(relative).relative_to('development')
            self.assertEqual(hashlib.sha256(committed.read_bytes()).hexdigest(), digest)
            self.assertEqual(regenerated.read_bytes(), committed.read_bytes())

    def test_schema_contracts_match(self):
        interface = (REPO / 'benchmarks/defects/SEALED-INTERFACE.md').read_text()
        interface, _ = interface.split('\n2026-09-24:', 1)
        self.assertIn(interface, __doc__)
        schema = interface[interface.index('**The schema the detectors read'):]
        for relative in ('gars/00_initialize_project/CONTEXT.md',
                         'gars/01_prepare_samplesheets/CONTEXT.md',
                         'docs/decisions/0101-row-8-defect-catalogue-and-detectors.md'):
            self.assertIn(schema, (REPO / relative).read_text())

    def test_development_exit(self):
        caught = 0
        graded = 0
        seen = len(list(self.root.iterdir()))
        for cid in range(1, 10):
            caught += int(grade(self.root / ('d%02d' % cid), cid, FLAGS[cid][0]))
            graded += 1
        false_flags = 0
        for i in range(1, 11):
            false_flags += int(not clean(self.root / ('c%02d' % i), all_stages=True))
            graded += 1
        print('planted-defects development (producer-authored, unsealed): %d/10 classes (placeholder 10 counted planted, not caught)' % caught)
        print('false flags (producer-authored clean projects): %d/10' % false_flags)
        print('graded %d of %d development projects seen' % (graded, seen))
        print('class 6: measured with --verify-integrity full; stage 01 default is none')
        self.assertEqual(len(CATALOGUE['entries']), 10)
        self.assertEqual(caught, 9)
        self.assertLessEqual(false_flags, 1)
        self.assertEqual(graded, seen)

    def test_sex_age_thresholds(self):
        for name, extra, flag, detail in (
                ('sex', {'sex': ['F', 'F', 'M', 'M']}, 'confounded_condition', 'sex'),
                ('imbalance', {'sex': ['F', 'F', 'F', 'M']}, 'covariate_imbalance', 'sex'),
                ('age', {'age': ['20', '22', '30', '32']}, 'covariate_imbalance', 'age')):
            root = self.root / name
            generate.project(root, extra=extra)
            self.assertTrue(grade(root, 3, flag, detail))
        code, result = stage(self.root / 'c08')
        self.assertEqual(code, 0)
        self.assertEqual(next(iter(result['assays'].values()))['design_check']['covariates'],
                         {'sex': 'not_checkable', 'age': 'not_checkable'})
        self.assertFalse(grade(self.root / 'c08', 3, 'covariate_imbalance'))

    def test_covariate_schema_refusals(self):
        for column, values in (('age', ['NA', 'unknown', '45y', 'nan', '-1', 'inf', '-inf']),
                               ('sex', ['f', 'm', 'female', 'male', '', 'Unknown'])):
            for i, value in enumerate(values):
                for assay in ('rnaseq_bulk', 'atacseq_bulk'):
                    with self.subTest(column=column, value=value, assay=assay):
                        root = self.root / (column + str(i) + assay)
                        extra = {column: ['20', '22', '40', value] if column == 'age'
                                 else ['F', 'F', 'M', value]}
                        generate.project(root, assay=assay, extra=extra)
                        code, result = stage(root)
                        self.assertEqual(code, 1)
                        self.assertIs(result['ok'], False)
                        failures = result['assays'][assay]['failures']
                        self.assertTrue(any(f['check'] == 'invalid_design' and column in f['detail']
                                            for f in failures))
                        self.assertEqual(result['wrote'], [])

    def test_class_specific_details(self):
        duplicate = self.root / 'duplicate'
        data = generate.project(duplicate)
        path = data / 'samples.csv'
        lines = path.read_text().splitlines()
        path.write_text('\n'.join(lines + [lines[1]]) + '\n')
        self.assertFalse(grade(duplicate, 2, 'invalid_design'))
        self.assertFalse(grade(self.root / 'd01', 3, 'confounded_condition'))
        self.assertTrue(grade(self.root / 'd03', 3, 'confounded_condition'))
        single = self.root / 'single'
        generate.project(single, conditions=['A', 'B', 'B'])
        self.assertTrue(grade(single, 2, 'invalid_design'))
        self.assertFalse(grade(single, 2, 'invalid_design', 'duplicate'))

    def test_sealed_grading_uses_class_details(self):
        # Metadata is supplied in memory for development controls, never a seal.
        duplicate = self.root / 'duplicate-control'
        data = generate.project(duplicate)
        path = data / 'samples.csv'
        lines = path.read_text().splitlines()
        path.write_text('\n'.join(lines + [lines[1]]) + '\n')
        declarations = {duplicate: (2, 'invalid_design'),
                        self.root / 'd01': (3, 'confounded_condition'),
                        self.root / 'd02': (2, 'insufficient_biological_replicates'),
                        self.root / 'd03': (3, 'confounded_condition')}
        real_read = Path.read_text
        def read(path, *args, **kwargs):
            if path.name == 'expected.json' and path.parent in declarations:
                cid, flag = declarations[path.parent]
                return json.dumps(dict(class_id=cid, expected_flag=flag,
                    expected_stage='01_prepare_samplesheets',
                    seal_type='independent_context', canary='a' * 32))
            return real_read(path, *args, **kwargs)
        with patch.object(Path, 'iterdir', return_value=iter(declarations)), \
                patch.object(Path, 'read_text', read), contextlib.redirect_stdout(io.StringIO()):
            caught, counts, totals = sealed_measure(self.root)
        self.assertEqual(counts[2], [1, 2])
        self.assertEqual(counts[3], [1, 2])
        self.assertEqual(totals['errors'], 0)
        self.assertEqual(totals['graded'], totals['seen'])
        self.assertEqual(sorted(totals['verdicts']),
                         [(2, 'caught'), (2, 'not_caught'), (3, 'caught'), (3, 'not_caught')])
        self.assertEqual(caught, 0)

    def test_row2_non_pseudoreplicate_controls(self):
        for name in ('batch-confounded', 'single-replicate'):
            with (REPO / 'benchmarks/fixtures' / (name + '.csv')).open() as handle:
                rows = list(csv.DictReader(handle))
            root = self.root / name
            generate.project(root, conditions=[r['condition'] for r in rows],
                             extra={key: [r[key] for r in rows]
                                    for key in ('batch', 'biological_unit')})
            _, result = stage(root)
            self.assertNotIn('pseudoreplication', [f['check'] for a in result['assays'].values()
                                                 for f in a['failures']])
        root = self.root / 'rna-single'
        generate.project(root, conditions=['A', 'B', 'B'])
        self.assertTrue(grade(root, 2, 'invalid_design',
                              'cannot be tested for differential expression'))

    def test_subject_replication(self):
        for column in ('subject', 'biological_unit'):
            for assay in ('rnaseq_bulk', 'atacseq_bulk'):
                root = self.root / (column + assay)
                generate.project(root, assay=assay, extra={column: ['d1', 'd1', 'd2', 'd2']})
                self.assertTrue(grade(root, 4, 'pseudoreplication'))
        root = self.root / 'subject-wins'
        generate.project(root, extra={'subject': ['d1', 'd2', 'd3', 'd4'],
                                     'biological_unit': ['x', 'x', 'y', 'y']})
        self.assertTrue(clean(root))

    def test_not_checkable_is_not_pass(self):
        root = self.root / 'noncasava'
        data = generate.project(root, extra={'library_index': ['ACGTACGT'] * 4})
        for path in (data / 'raw').iterdir():
            path.write_text('@noncasava\nACGT\n+\nIIII\n')
        for project in (root, self.root / 'c01'):
            code, result = stage(project)
            self.assertEqual(code, 0)
            self.assertEqual(next(iter(result['assays'].values()))['sample_label_check']['outcome'], 'not_checkable')
            self.assertFalse(grade(project, 5, 'sample_label_mismatch'))

    def test_case_whitespace_lanes_and_order(self):
        for cid in (1, 3, 4, 5):
            root = self.root / ('d%02d' % cid)
            path = next((root / '00_data').glob('*/samples.csv'))
            lines = path.read_text().splitlines()
            path.write_text(','.join(' ' + x.upper() + ' ' for x in lines[0].split(',')) +
                            '\n' + '\n'.join(reversed(lines[1:])) + '\n')
            self.assertTrue(grade(root, cid, FLAGS[cid][0]))
        root = self.root / 'lanes'
        data = generate.project(root, extra={'library_index': ['ACGTACGT+TTGACCAA'] * 4}, lanes=2, zipped=True)
        # Whole dual indexes are compared; adding lanes does not hide a swapped sample.
        sample = data / 'samples.csv'
        sample.write_text(sample.read_text().replace('ACGTACGT+TTGACCAA', 'ACGTACGT+AAAAAAAA'))
        self.assertTrue(grade(root, 5, 'sample_label_mismatch'))
        _, result = stage(root)
        details = [f['detail'] for a in result['assays'].values() for f in a['failures']
                   if f['check'] == 'sample_label_mismatch']
        self.assertEqual(details, ['sample_label_mismatch: 4 mismatched samples'])

    def test_collect_diagnostic_drift(self):
        tables = [
            ([(None, .01), (None, .04), (.1, .1)], False),
            ([(.01, .01), (.04, .04)], False), ([(.01, .005), (.04, .04)], False),
            ([(.01, .03), (.04, .06)], False), ([(None, None)], False), ([(.1, .09999999)], False),
            ([(.1, .2)], False), ([(.1, .1)], True), ([(.01, .02), (.04, .04)], True)]
        for i, (pairs, expected) in enumerate(tables):
            path = self.root / ('table%d.csv' % i)
            generate.table(path, pairs)
            code, result = collect(path)
            diag, payload = cli(DE, ['check-table', '--table', path])
            self.assertEqual(code == 0, expected)
            self.assertEqual(diag == 0, expected)
            self.assertEqual([f['check'] for f in result['failures']],
                             [f['check'] for f in payload['failures']])
        code, _ = collect(self.root / 'c02/de_results.csv')
        self.assertEqual(code, 0, 'six significant digits must pass')

    def test_row1_mapping_detail_family(self):
        for detail in GROUP_ONE_FAMILY:
            self.assertEqual(row1_class({'reason': 'invalid_design', 'detail_contains': detail}), 2)
        self.assertIsNone(row1_class({'reason': 'invalid_design', 'detail_contains': 'duplicate'}))
        self.assertIsNone(row1_class({'reason': 'subject_nesting', 'detail_contains': 'subject'}))


class SealedCatalogueTests(unittest.TestCase):
    def test_sealed_catalogue(self):
        root = os.environ.get('GARS_SEALED_DEFECT_FIXTURES')
        if not root:
            self.skipTest('sealed catalogue unmeasured')
        caught, counts, totals = sealed_measure(root, os.environ.get('GARS_SEALED_DESIGN_FIXTURES'))
        self.assertEqual(totals['graded'], totals['seen'], 'sealed accounting mismatch')
        self.assertEqual(totals['errors'], 0, 'sealed plant error')
        self.assertGreaterEqual(totals['independent_context'] + totals['external_human_seal'], 3)
        self.assertGreaterEqual(caught, 9, 'sealed catalogue threshold not met')
        self.assertGreater(totals['clean'], 0, 'sealed clean unmeasured')
        self.assertLessEqual(totals['flagged'] * 10, totals['clean'])


class SealedOutputDisciplineTests(unittest.TestCase):
    def test_sealed_class9_uses_live_transport(self):
        # Producer-authored layout control, never a seal or live measurement.
        reference = '10.5555/gars-d1-outside-protocol-fixtures'
        resolver = emitter.evidence_check.resolve_citation
        requests = []
        def not_found(url):
            requests.append(url)
            return (404, b'{}') if 'crossref' in url else (404, b'{"responseCode":100}')
        with tempfile.TemporaryDirectory(prefix='defect-doi-origin-') as folder:
            root = Path(folder)
            plant = root / 'p01'
            plant.mkdir()
            generate.claims(plant, reference=reference)
            generate.write_json(plant / 'expected.json', dict(
                class_id=9, expected_flag='citation_unresolved', expected_stage='report_emit',
                seal_type='independent_context', canary='a' * 32))
            with patch.object(resolver, 'live_transport', side_effect=not_found), \
                    patch.object(emitter, 'main', wraps=emitter.main) as emit, \
                    contextlib.redirect_stdout(io.StringIO()):
                caught, counts, totals = sealed_measure(root)
                self.assertEqual(counts[9], [1, 1])
                self.assertEqual(totals['verdicts'], [(9, 'caught')])
                self.assertEqual(totals['errors'], 0)
                self.assertEqual(totals['graded'], totals['seen'])
                self.assertIsNone(emit.call_args[1]['transport'])
                self.assertFalse(Path(emit.call_args[0][0][-1]).exists())
                self.assertEqual(requests, [
                    'https://api.crossref.org/works/10.5555%2Fgars-d1-outside-protocol-fixtures',
                    'https://doi.org/api/handles/10.5555%2Fgars-d1-outside-protocol-fixtures'])
                # Development still uses replay, so this unrecorded DOI cannot score.
                requests[:] = []
                self.assertFalse(grade(plant, 9, 'citation_unresolved'))
                self.assertIs(emit.call_args[1]['transport'], replay)
                self.assertEqual(requests, [])
                generate.claims(plant, reference=generate.FAKE_DOI)
                self.assertTrue(grade(plant, 9, 'citation_unresolved'))
                self.assertEqual(requests, [])

    def test_sentinel_and_error_accounting(self):
        sentinel = 'CONTENT_SENTINEL_801'
        with tempfile.TemporaryDirectory(prefix='defect-output-') as folder:
            root = Path(folder)
            plant = root / ('p01_' + sentinel)
            data = generate.project(plant, extra={'plant_note': [sentinel] * 4})
            path = data / 'samples.csv'
            path.write_text(path.read_text().replace('DEV', sentinel))
            (data / 'raw' / (sentinel + '.fastq')).write_text(sentinel)
            generate.write_json(plant / 'expected.json', dict(
                class_id=4, expected_flag='pseudoreplication', expected_stage='01_prepare_samplesheets',
                seal_type='independent_context', canary='a' * 32, extra=sentinel))
            bad = root / ('p02_' + sentinel)
            bad.mkdir()
            (bad / 'expected.json').write_text(sentinel)
            def raises(*args):
                print(sentinel)
                print(sentinel, file=sys.stderr)
                raise ValueError(sentinel)
            output = io.StringIO()
            with patch(__name__ + '.grade', side_effect=raises), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                caught, counts, totals = sealed_measure(root)
            self.assertNotIn(sentinel, output.getvalue())
            self.assertEqual(totals['seen'], 2)
            self.assertEqual(totals['graded'], 2)
            self.assertEqual(totals['errors'], 2)
            self.assertEqual(totals['verdicts'], [(4, 'error'), (None, 'error')])
            self.assertEqual(counts[4], [0, 1])
            self.assertEqual(counts[10], [0, 1])
            self.assertEqual(caught, 0)

    def test_sealed_class_output(self):
        with tempfile.TemporaryDirectory(prefix='defect-class-') as folder:
            root = Path(folder)
            plant = root / 'p01'
            plant.mkdir()
            sentinel = 'CLASS_SENTINEL_801'
            (plant / 'expected.json').write_text(sentinel)
            output = io.StringIO()
            with patch.dict(os.environ, {'GARS_SEALED_DEFECT_FIXTURES': str(root),
                                        'GARS_SEALED_DESIGN_FIXTURES': ''}), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = unittest.TextTestRunner(stream=output).run(
                    unittest.TestSuite([SealedCatalogueTests('test_sealed_catalogue')]))
            self.assertFalse(result.wasSuccessful())
            self.assertNotIn(sentinel, output.getvalue())
            self.assertIn('sealed graded 1 of 1 plants seen', output.getvalue())

    def test_unmapped_outside_arithmetic(self):
        with tempfile.TemporaryDirectory(prefix='defect-map-') as folder:
            root = Path(folder)
            old = root / 'old'
            old.mkdir()
            plant = old / 'p01'
            plant.mkdir()
            generate.write_json(plant / 'expected.json', dict(reason='invalid_design',
                detail_contains='duplicate', seal_type='independent_context'))
            empty = root / 'new'
            empty.mkdir()
            with contextlib.redirect_stdout(io.StringIO()):
                caught, counts, totals = sealed_measure(empty, old)
            self.assertEqual(totals['unmapped'], 1)
            self.assertEqual(totals['verdicts'], [(None, 'unmapped')])
            self.assertEqual(totals['mapped'], 0)
            self.assertEqual(counts[2], [0, 0])
            self.assertEqual(caught, 0)
            self.assertEqual(totals['graded'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
