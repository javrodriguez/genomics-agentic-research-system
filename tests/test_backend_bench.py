"""Backend instrument controls; no timings measured or evidence rows published."""
import ast
import copy
import csv
import gzip
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
REPO=Path(__file__).resolve().parents[1]
INSTRUMENT=REPO / 'scripts/backend_bench.py'
if not INSTRUMENT.is_file():
    raise ImportError('missing scripts/backend_bench.py')
spec=importlib.util.spec_from_file_location('backend_bench',str(INSTRUMENT))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


class BackendBenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        marker=patch.object(b.ex,'HOMELAB_MARKER',str(self.root / 'operator-marker'))
        marker.start();self.addCleanup(marker.stop)

    def evidence(self):
        return dict(backend='local',venue='local',status='COMPLETED',workload_id='W1',
                    workload_sha256=b.expected_workload_sha256(),samples=24,wall_s=1.0,cpu_s=0.5,
                    max_rss_mb=8.0,queue_wait_s=0,python_version='3.6.8',gars_commit='a'*40,
                    measured_at='2026-09-25T12:00:00Z',cost_usd_per_sample='unmetered',cost_basis='owned_hardware')

    def test_committed_rows_regenerate_and_privacy(self):
        path=REPO / 'benchmarks/backend_bench.csv'
        with path.open(newline='') as handle:
            reader=csv.DictReader(handle);rows=list(reader)
            self.assertEqual(reader.fieldnames,b.CSV_FIELDS)
        active=b.verify_rows(rows,REPO / 'benchmarks/backend_bench')
        backends=sorted(key[0] for key in active)
        print('backend rows: %d/3 (%s)' % (len(backends), ', '.join(backends)))
        for path in (REPO / 'benchmarks/backend_bench').glob('*.json'):
            b.validate_evidence(json.loads(path.read_text()))

    def test_w1_bytes_and_units_and_python36(self):
        one=b.blob(1)
        self.assertEqual(one,b.blob(1))
        self.assertNotEqual(one,b.blob(2))
        self.assertEqual(len(gzip.decompress(one)),8*1024**2)
        self.assertGreater(len(one),8*1024**2)
        self.assertEqual(b.rss_mb(1024,'linux'),1)
        self.assertEqual(b.rss_mb(1024**2,'darwin'),1)
        ast.parse(INSTRUMENT.read_text(),feature_version=(3,6))

    def test_run_real_prepared_door_without_measurement(self):
        out=self.root / 'bench'
        with patch.object(b.ex,'_submit_once',return_value=('42',None)) as scheduler:
            submitted=b.run('local',out)
            scheduler.assert_called_once()
        self.assertEqual(submitted['job_id'],'42')
        self.assertEqual(submitted['workload_sha256'],b.expected_workload_sha256())
        self.assertFalse((out / 'evidence.json').exists())
        self.assertFalse((out / b.STAGE / 'run/result.json').exists())
        self.assertEqual(b.ex.stage_record(out,out / b.STAGE)['venue'],'local')
        self.assertEqual(b.wl.dataset_record(out)['purpose'],'fixture')
        self.assertEqual(len(list((out / 'workload').glob('w1-*.bin.gz'))),24)
        with self.assertRaisesRegex(ValueError,'output_already_exists'):
            b.run('local',out)
        with self.assertRaisesRegex(ValueError,'venue_host_mismatch'):
            b.run('homelab',self.root / 'absent-marker')
        Path(b.ex.HOMELAB_MARKER).touch()
        with self.assertRaisesRegex(ValueError,'venue_host_mismatch'):
            b.run('local',self.root / 'marked-local')

    def test_collection_waits_for_terminal_and_failure_never_appends(self):
        for terminal in ('COMPLETED','FAILED'):
            root=self.root / terminal;root.mkdir()
            (root / b.STAGE / 'run').mkdir(parents=True)
            e=self.evidence()
            (root / 'submitted.json').write_text(json.dumps(dict(venue='local',job_id='42',workload_sha256=e['workload_sha256'])))
            timing={k:e[k] for k in ('wall_s','cpu_s','max_rss_mb','python_version','workload_sha256')}
            timing['ok']=terminal=='COMPLETED'
            (root / b.STAGE / 'run/result.json').write_text(json.dumps(timing))
            answers=iter(('PENDING','RUNNING',terminal))
            def poll(*args):
                self.assertFalse((root / 'evidence.json').exists())
                return next(answers),None
            with patch.object(b.ex,'status',side_effect=poll) as scheduler,patch.object(b.time,'sleep'):
                actual=b.collect(root)
            self.assertEqual(scheduler.call_count,3)
            self.assertEqual(actual['status'],terminal)
            if terminal=='FAILED':
                with self.assertRaisesRegex(ValueError,'evidence_not_completed'):
                    b.append(root / 'evidence.json')
            (root / 'evidence.json').unlink()
            with patch.object(b.ex,'status',return_value=('PENDING',None)),self.assertRaisesRegex(ValueError,'collection_timeout'):
                b.collect(root,timeout_s=0)
            self.assertFalse((root / 'evidence.json').exists())
        result=root / b.STAGE / 'run/result.json';result.unlink()
        with patch.object(b.ex,'status',return_value=('FAILED:EXIT_137',None)):
            self.assertIsNone(b.collect(root)['wall_s'])

    def test_append_regeneration_supersession_and_tampering(self):
        csv_path=self.root / 'bench.csv';evidence_dir=self.root / 'evidence'
        with csv_path.open('w',newline='') as handle:
            csv.writer(handle,lineterminator='\n').writerow(b.CSV_FIELDS)
        evidence=self.root / 'candidate.json';e=self.evidence();evidence.write_text(json.dumps(e))
        with patch.object(b,'CSV_PATH',csv_path),patch.object(b,'EVIDENCE_DIR',evidence_dir):
            first=b.append(evidence)
            with self.assertRaisesRegex(ValueError,'supersede_required'):
                b.append(evidence)
            e['wall_s']=2.0;evidence.write_text(json.dumps(e))
            second=b.append(evidence,supersede=first['evidence_sha256'])
            self.assertEqual(second['supersedes'],first['evidence_sha256'])
            with csv_path.open() as handle: rows=list(csv.DictReader(handle))
            self.assertEqual(len(rows),2)
            b.verify_rows(rows,evidence_dir)
            altered=copy.deepcopy(rows);altered[0]['wall_s']='999'
            with self.assertRaisesRegex(ValueError,'csv_evidence_mismatch'):
                b.verify_rows(altered,evidence_dir)
            path=evidence_dir / (first['evidence_sha256']+'.json');path.unlink()
            with self.assertRaisesRegex(ValueError,'evidence_missing'):
                b.verify_rows(rows,evidence_dir)
        for field,value in [('hostname','synthetic-host'),('user','synthetic-user'),('path','synthetic/path'),
                            ('wall_s',-1),('cpu_s',float('nan')),('workload_sha256','0'*64),
                            ('cost_usd_per_sample',1.2),('cost_basis','hand-entered')]:
            altered=dict(e);altered[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                b.validate_evidence(altered)

    def test_slurm_accounting_uses_batch_rss(self):
        from types import SimpleNamespace
        main=b'2026-09-25T00:00:00|2026-09-25T00:00:05|2026-09-25T00:00:15|00:00:10|00:00:08|1K|COMPLETED|\n'
        batch=main.replace(b'|1K|',b'|2048K|')
        with patch.object(b.subprocess,'run',side_effect=[SimpleNamespace(returncode=0,stdout=main),SimpleNamespace(returncode=0,stdout=batch)]) as scheduler:
            result=b.slurm_timings('42')
        self.assertEqual(result,dict(wall_s=10,cpu_s=8,max_rss_mb=2,queue_wait_s=5))
        self.assertIn('42.batch',scheduler.call_args[0][0])


if __name__=='__main__':
    unittest.main(verbosity=2)
