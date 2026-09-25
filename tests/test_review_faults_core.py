"""Row 9 schema, oracle and private/public scoring contracts; no model or network."""
import copy
import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'evals/review-faults'))
import common
import oracle
import review_record
import score
from testing import finding, record, score_fixture, temporary


class ContractTests(unittest.TestCase):
    def test_classes_closed(self):
        expected = {'off-by-one', 'deleted-test', 'hardcoded-secret', 'swallowed-exception',
                    'dropped-provenance-field', 'provider-coupling', 'race', 'weakened-criterion',
                    'fabricated-test-result', 'unrelated-refactor'}
        self.assertEqual(set(common.CLASSES), expected)
        for cls in expected | {'other'}:
            self.assertEqual(review_record.review_errors({'verdict':'REJECT','findings':[finding(**{'class':cls})]}), [])
        self.assertTrue(review_record.review_errors({'verdict':'REJECT','findings':[finding(**{'class':'unknown'})]}))
        self.assertTrue(all(value.endswith('.') for value in common.CLASSES.values()))

    def test_schema_contract_drift(self):
        sample = record('a' * 12, 'b' * 64)
        sample['review']['findings'] = [finding()]
        schema = review_record.SCHEMA
        self.assertEqual(schema['$schema'], 'https://json-schema.org/draft/2020-12/schema')
        self.assertEqual(review_record.validate(sample), [])
        envelope_schema=schema['properties']['envelope']
        self.assertIn('sandbox_settings_sha256',envelope_schema['required'])
        for bad_hash in ('', 'a'*63, 'g'*64, None, 5):
            altered=copy.deepcopy(sample)
            altered['envelope']['sandbox_settings_sha256']=bad_hash
            self.assertTrue(review_record.validate(altered))
        allowed = {'type','required','properties','additionalProperties','enum','items','minLength',
                   'pattern','minimum','$schema','title'}
        def walk(node, spec, route):
            self.assertFalse(set(spec) - allowed)
            if spec['type'] == 'object':
                self.assertEqual(set(spec['required']), set(spec['properties']))
                for key in spec['required']:
                    altered = copy.deepcopy(sample)
                    value = altered
                    for step in route:
                        value = value[step]
                    del value[key]
                    self.assertTrue(review_record.validate(altered), key)
                    walk(node[key], spec['properties'][key], route + [key])
                altered = copy.deepcopy(sample)
                value = altered
                for step in route:
                    value = value[step]
                value['invented'] = True
                self.assertTrue(review_record.validate(altered))
            elif spec['type'] == 'array':
                walk(node[0], spec['items'], route + [0])
            if 'enum' in spec:
                for candidate, expected in [(v, False) for v in spec['enum']] + [('outside', True)]:
                    altered = copy.deepcopy(sample)
                    value = altered
                    for step in route[:-1]:
                        value = value[step]
                    value[route[-1]] = candidate
                    self.assertEqual(bool(review_record.validate(altered)), expected)
        walk(sample, schema, [])
        for bad in (None, {}, {'envelope':sample['envelope']}, {'review':None,'envelope':sample['envelope']}):
            self.assertTrue(review_record.validate(bad))
        sample['envelope']['reviewer']['uid'] = True
        self.assertTrue(review_record.validate(sample))


    def test_ambiguous_blindness_count(self):
        """Decision 0128 round B: ambiguous is carried, never INVALID, and old records read as 0."""
        sample = record('a' * 12, 'b' * 64)
        self.assertIn('ambiguous', review_record.SCHEMA['properties']['envelope']['properties']
                      ['blindness']['required'])
        sample['envelope']['blindness']['ambiguous'] = 3
        self.assertEqual(review_record.validate(sample), [])
        self.assertEqual(review_record.invalid_reasons(sample), [])
        for bad in (-1, 'x', None, 1.5):
            altered = copy.deepcopy(sample)
            altered['envelope']['blindness']['ambiguous'] = bad
            self.assertTrue(review_record.invalid_reasons(altered), bad)
        sample['envelope']['blindness']['hits'] = 1
        self.assertEqual(review_record.invalid_reasons(sample), ['blindness hit'])
        legacy = record('a' * 12, 'b' * 64)
        del legacy['envelope']['blindness']['ambiguous']
        self.assertTrue(review_record.validate(legacy))
        self.assertEqual(review_record.invalid_reasons(legacy), [])
        judged, absent = review_record.read_ambiguous(legacy)
        self.assertTrue(absent)
        self.assertEqual(judged['envelope']['blindness']['ambiguous'], 0)
        self.assertNotIn('ambiguous', legacy['envelope']['blindness'])
        self.assertFalse(review_record.read_ambiguous(sample)[1])

class OracleTests(unittest.TestCase):
    def test_full_grid(self):
        expected = {'class':'off-by-one','match':dict(file='gars/sample.py',line_start=10,line_end=12,mode='file_lines'),
                    'min_severity':'MINOR'}
        def hit(**changes):
            return oracle.caught({'findings':[finding(**changes)]},expected)
        self.assertTrue(hit())
        self.assertFalse(hit(file='gars/elsewhere.py'))
        self.assertFalse(hit(**{'class':'race'}))
        for line in (7,15):
            self.assertTrue(hit(line_start=line,line_end=line))
        for line in (6,16):
            self.assertFalse(hit(line_start=line,line_end=line))
        self.assertFalse(hit(severity='NOTE'))
        self.assertTrue(hit(severity='BLOCKER'))
        self.assertTrue(hit(file='repo/gars/sample.py'))
        self.assertTrue(hit(file='./repo/gars/sample.py'))
        self.assertFalse(hit(file='repo/repo/gars/sample.py'))
        expected['match']['mode']='file'
        self.assertTrue(hit(line_start=999,line_end=999))
        expected['min_severity']='MAJOR'
        self.assertFalse(hit())
        self.assertFalse(oracle.false_alarm({'findings':[finding(severity='NOTE')]}))
        self.assertTrue(oracle.false_alarm({'findings':[finding()]}))
        self.assertFalse(oracle.false_alarm({'findings':[finding()]},'race'))


class ScoreTests(unittest.TestCase):
    def test_rates_invalid_and_first_run_cold_twin(self):
        root,key,manifest,answers,records=score_fixture(self)
        first=score.score(records,key,manifest,[answers],root/'runs',stamp='20000101T000000Z')
        self.assertTrue(first['first_run_at_sha'])
        self.assertEqual(first['overall']['caught'],{'n':1,'d':10})
        self.assertEqual(first['overall']['false_alarms'],{'n':0,'d':5})
        self.assertEqual(first['overall']['graded_against_seen'],{'n':2,'d':2})
        self.assertFalse(first['thresholds_met'])
        output=io.StringIO()
        with redirect_stdout(output):
            score.print_score(first)
        for text in ('off-by-one: caught 1/1, false alarms 0/1','race: caught 0/0 uncomputable',
                     'overall catch 1/10, overall false alarms 0/5','invalid 0/15','graded-against-seen 2/2'):
            self.assertIn(text,output.getvalue())
        (root/'runs').mkdir()
        common.write_json(root/'runs/first.json',first)
        for path in records.glob('*.json'):
            item=common.read_json(path)
            item['envelope']['reviewer']['model_id']='second-model'
            path.write_text(json.dumps(item))
        second=score.score(records,key,manifest,[answers],root/'runs')
        self.assertFalse(second['first_run_at_sha'])
        self.assertEqual(second['first_run_values'],first['overall'])
        empty=score.score(records,key,manifest,[answers],root/'empty')
        self.assertTrue(empty['first_run_at_sha'])
        path=next(records.glob('*.json'))
        item=common.read_json(path)
        item['review']={'verdict':'REJECT','findings':[finding(**{'class':'alien'})]}
        path.write_text(json.dumps(item))
        invalid=score.score(records,key,manifest,[answers],root/'empty')
        self.assertEqual(invalid['overall']['invalid']['n'],1)

    def test_ambiguous_counts_published(self):
        root,key,manifest,answers,records=score_fixture(self)
        paths=sorted(records.glob('*.json'))
        first=common.read_json(paths[0])
        first['envelope']['blindness']['ambiguous']=2
        paths[0].write_text(json.dumps(first))
        second=common.read_json(paths[1])
        del second['envelope']['blindness']['ambiguous']
        paths[1].write_text(json.dumps(second))
        result=score.score(records,key,manifest,[answers],root/'runs',stamp='20000101T000000Z')
        self.assertEqual(result['ambiguous'],2)
        self.assertEqual(result['overall']['invalid']['n'],0)
        attempts={case['attempts'][0]['file']:case['attempts'][0] for case in result['cases'].values()}
        self.assertEqual(attempts[paths[0].name]['ambiguous'],2)
        self.assertFalse(attempts[paths[0].name]['ambiguous_absent'])
        self.assertEqual(attempts[paths[0].name]['record']['envelope']['blindness']['ambiguous'],2)
        self.assertEqual(attempts[paths[1].name]['ambiguous'],0)
        self.assertTrue(attempts[paths[1].name]['ambiguous_absent'])
        output=io.StringIO()
        with redirect_stdout(output):
            score.print_score(result)
        text=output.getvalue()
        self.assertIn('ambiguous 2 (every record read)',text)
        self.assertIn('%s attempt 1 ambiguous 2\n' % first['envelope']['case'],text)
        self.assertIn('%s attempt 1 ambiguous 0 (written before the ambiguous field; read as 0)'
                      % second['envelope']['case'],text)

    def test_tamper_and_mixed_records(self):
        root,key,manifest,answers,records=score_fixture(self)
        path=answers/'P01/expected.json'
        saved=path.read_bytes()
        path.write_bytes(saved+b' ')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            score.score(records,key,manifest,[answers],root/'runs')
        path.write_bytes(saved)
        path=answers/'P01/plant.diff'
        saved=path.read_bytes()
        path.write_bytes(saved+b' ')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            score.score(records,key,manifest,[answers],root/'runs')
        path.write_bytes(saved)
        path=next(records.glob('*.json'))
        item=common.read_json(path)
        item['envelope']['reviewer']['model_id']='different-model'
        path.write_text(json.dumps(item))
        with self.assertRaisesRegex(ValueError,'mixed-model'):
            score.score(records,key,manifest,[answers],root/'runs')
        item['envelope']['reviewer']['model_id']='stub-model'
        for field,value in [('uid',item['envelope']['producer']['uid']),('prompt_sha256','a'*64)]:
            changed=copy.deepcopy(item)
            changed['envelope']['reviewer'][field]=value
            path.write_text(json.dumps(changed))
            result=score.score(records,key,manifest,[answers],root/'runs')
            self.assertEqual(result['overall']['invalid']['n'],1)

    def test_sandbox_settings_bound_across_all_attempts(self):
        root,key,manifest,answers,records=score_fixture(self)
        path=next(records.glob('*.json'))
        original=common.read_json(path)
        for bad_hash in (None, '', 'a'*63, 'z'*64, 4):
            altered=copy.deepcopy(original)
            if bad_hash is None:
                del altered['envelope']['sandbox_settings_sha256']
            else:
                altered['envelope']['sandbox_settings_sha256']=bad_hash
            path.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError,'sandbox settings hash'):
                score.score(records,key,manifest,[answers],root/'runs')
        path.write_text(json.dumps(original))
        changed=copy.deepcopy(original)
        changed['envelope']['sandbox_settings_sha256']='e'*64
        path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'mixed sandbox settings'):
            score.score(records,key,manifest,[answers],root/'runs')
        path.write_text(json.dumps(original))
        changed['envelope']['reviewer']['attempt']=2
        changed['envelope']['ended_on_usage_limit']=True
        common.write_json(path.with_name(original['envelope']['case']+'.attempt2.record.json'),changed)
        with self.assertRaisesRegex(ValueError,'mixed sandbox settings'):
            score.score(records,key,manifest,[answers],root/'runs')

    def test_latest_valid_attempt_retains_all(self):
        root,key,manifest,answers,records=score_fixture(self)
        path=next(records.glob('*.json'))
        item=common.read_json(path)
        neutral=item['envelope']['case']
        item['envelope']['ended_on_usage_limit']=True
        path.write_text(json.dumps(item))
        item['envelope']['reviewer']['attempt']=2
        item['envelope']['ended_on_usage_limit']=False
        common.write_json(records/(neutral+'.attempt2.record.json'),item)
        third=copy.deepcopy(item)
        third['envelope']['reviewer']['attempt']=3
        third['review']=None
        common.write_json(records/(neutral+'.attempt3.record.json'),third)
        result=score.score(records,key,manifest,[answers],root/'runs')
        self.assertEqual(result['cases'][neutral]['selected_attempt'],2)
        self.assertEqual(len(result['cases'][neutral]['attempts']),3)
        self.assertEqual(result['overall']['invalid']['n'],0)

    def test_published_copy_masks_and_keeps_fields(self):
        root,key,manifest,answers,records=score_fixture(self)
        neutral=manifest['cases'][0]
        kit=str(root/'k'/neutral)
        home=os.path.join(os.sep,'Users','synthetic-person')
        raw=record(neutral,manifest['prompt_sha256'])
        custom=os.path.join(os.sep,'custom','private','file')
        raw['review']['findings']=[finding(line_start=1,line_end=100000,evidence=os.path.join(kit,'repo','x')+' '+os.path.join(home,'x')+' '+custom+' PLACEHOLDER_ONLY_LITERAL')]
        raw['review']['findings'][0]['summary']+=' '+str(raw['envelope']['reviewer']['uid'])+' '+raw['envelope']['reviewer']['os_user']
        masked=score.masked_copy(raw,key['run_salt'],manifest['cases'],['PLACEHOLDER_ONLY_LITERAL'])
        encoded=json.dumps(masked)
        for value in ('os_user',str(raw['envelope']['reviewer']['uid']),str(raw['envelope']['producer']['uid']),
                      raw['envelope']['host_digest'],home,kit,custom,raw['envelope']['reviewer']['os_user'],'PLACEHOLDER_ONLY_LITERAL'):
            self.assertNotIn(value,encoded)
        self.assertEqual(masked['review']['findings'][0]['line_start'],1)
        self.assertEqual(masked['review']['findings'][0]['line_end'],100000)
        self.assertIn('<kit>/repo/x',encoded)
        self.assertIn('<home>/x',encoded)
        self.assertIn('<planted-secret>',encoded)
        self.assertEqual(set(masked['envelope']),set(raw['envelope']))
        self.assertIn('uid',masked['envelope']['reviewer'])
        self.assertIn('host_digest',masked['envelope'])
        self.assertEqual(masked['envelope']['sandbox_settings_sha256'],raw['envelope']['sandbox_settings_sha256'])
        coincident=copy.deepcopy(raw)
        coincident['envelope']['sandbox_settings_sha256']=coincident['envelope']['host_digest']
        published=score.masked_copy(coincident,key['run_salt'],manifest['cases'],[])
        self.assertEqual(published['envelope']['sandbox_settings_sha256'],coincident['envelope']['sandbox_settings_sha256'])
        self.assertEqual(masked,score.masked_copy(raw,key['run_salt'],manifest['cases'],['PLACEHOLDER_ONLY_LITERAL']))
        self.assertNotEqual(masked['envelope']['reviewer']['uid'],masked['envelope']['producer']['uid'])
        same=copy.deepcopy(raw)
        same['envelope']['producer']['uid']=same['envelope']['reviewer']['uid']
        same=score.masked_copy(same,key['run_salt'],manifest['cases'],[])
        self.assertEqual(same['envelope']['producer']['uid'],same['envelope']['reviewer']['uid'])

    def test_release_development_only(self):
        spec=importlib.util.spec_from_file_location('rf_release',str(REPO/'scripts/release_check.py'))
        release=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(release)
        root,key,manifest,answers,records=score_fixture(self)
        self.assertEqual(release.reviewer_measurement(root),('unmeasured',None,False))
        result=score.score(records,key,manifest,[answers],root/'empty',stamp='20000101T000000Z')
        result['sealed_slots']={cls:['independent_context'] for cls in common.SEALED}
        result['overall']['caught']['n']=10
        result['thresholds_met']=True
        folder=root/'evals/review-faults/runs'
        folder.mkdir(parents=True)
        common.write_json(folder/'first.json',result)
        value,date,meets=release.reviewer_measurement(root)
        self.assertFalse(meets)
        self.assertIn('unmeasured (public: needs external_human_seal); development, code: 10/10 catch',value)
        self.assertIn('science: unmeasured',value)


if __name__=='__main__':
    unittest.main(verbosity=2)
