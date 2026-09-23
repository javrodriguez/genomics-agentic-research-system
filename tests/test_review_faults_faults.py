"""Visible guard faults, each observed red in an isolated copy; no sealed score."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
# Same fault-list shape as gars/tests/test_lifecycle_faults.py: label, file,
# old bytes, replacement, named acceptance module and test. These are controls.
FAULTS = [
    ('repository bytes nondeterministic','build_cases.py','salt = run_salt or secrets.token_hex(16)','salt = secrets.token_hex(16)','build','BuildTests.test_determinism_history_and_private_key'),
    ('extra repository history','build_cases.py',"parent = commit(repo, 'Initial source snapshot')","parent = commit(repo, 'Initial source snapshot')\n        parent = commit(repo, 'Extra history', parent)",'build','BuildTests.test_determinism_history_and_private_key'),
    ('key enters case folder','build_cases.py',"write_json(output / 'key.json', key)","write_json(output / 'key.json', key)\n    write_json(repo / 'key.json', key)",'build','BuildTests.test_determinism_history_and_private_key'),
    ('collision guard removed','build_cases.py','if len(set(ids.values())) != len(ids):','if False:','build','BuildTests.test_build_refusals'),
    ('nonapplying plant accepted','build_cases.py',"raise ValueError('plant does not apply: ' + cid)",'pass','build','BuildTests.test_build_refusals'),
    ('invalid case hidden','score.py','invalid += 1','invalid += 0','core','ScoreTests.test_rates_invalid_and_first_run_cold_twin'),
    ('catch numerator inflated','score.py','total_caught += int(hit)','total_caught += 2','core','ScoreTests.test_rates_invalid_and_first_run_cold_twin'),
    ('account name published','score.py',"if k != 'os_user'",'if True','core','ScoreTests.test_published_copy_masks_and_keeps_fields'),
    ('raw host digest published','score.py','return digest(item)',"return item if key == 'host_digest' else digest(item)",'core','ScoreTests.test_published_copy_masks_and_keeps_fields'),
    ('kit prefix published','score.py',"item = re.sub(pattern, '<kit>', item)",'item = item','core','ScoreTests.test_published_copy_masks_and_keeps_fields'),
    ('home prefix published','score.py',"item = re.sub(pattern, '<home>', item)",'return item','core','ScoreTests.test_published_copy_masks_and_keeps_fields'),
    ('oracle ignores class','oracle.py',"if finding['class'] != expected['class']:", 'if False:', 'core','OracleTests.test_full_grid'),
    ('oracle ignores file','oracle.py',"if normalize_file(finding['file']) != target['file']:",'if False:','core','OracleTests.test_full_grid'),
    ('line tolerance widened','oracle.py',"target['line_end'] + 3", "target['line_end'] + 4",'core','OracleTests.test_full_grid'),
    ('min severity ignored','oracle.py',"if SEVERITY[finding['severity']] < SEVERITY[expected.get('min_severity', 'MINOR')]:",'if False:','core','OracleTests.test_full_grid'),
    ('file mode ignored','oracle.py',"target['mode'] == 'file' or (",'False or (','core','OracleTests.test_full_grid'),
    ('repository prefix retained','oracle.py',"name = name[5:]",'name = name','core','OracleTests.test_full_grid'),
    ('NOTE becomes alarm','oracle.py',"SEVERITY['MINOR'] and", "SEVERITY['NOTE'] and",'core','OracleTests.test_full_grid'),
    ('closed enum ignored','review_record.py',"if 'enum' in schema and value not in schema['enum']:",'if False:','core','ContractTests.test_classes_closed'),
    ('required fields ignored','review_record.py',"for key in schema.get('required', []):",'for key in []:','core','ContractTests.test_schema_contract_drift'),
    ('envelope taken from stub text','run_reviews.py','        write_json(output, record)',"        record['envelope'].update(events[0].get('envelope', {}))\n        write_json(output, record)",'launch','LaunchTests.test_envelope_and_command_are_code_owned'),
    ('producer uid check removed','run_reviews.py','if uid == producer.pw_uid:','if False:','launch','LaunchTests.test_identity_refusals'),
    ('unresolved producer account accepted','run_reviews.py',"raise ValueError('producer-account does not resolve on this host')",'return ({}, {})','launch','LaunchTests.test_identity_refusals'),
    ('root uid allowed','run_reviews.py','if uid == 0:','if False:','launch','LaunchTests.test_identity_refusals'),
    ('missing model allowed','run_reviews.py','if not args.model:','if False:','launch','LaunchTests.test_api_model_and_prompt_refusals'),
    ('API key allowed','run_reviews.py',"if 'ANTHROPIC_API_KEY' in os.environ:",'if False:','launch','LaunchTests.test_api_model_and_prompt_refusals'),
    ('prompt hash not checked','run_reviews.py',"if sha256(prompt) != manifest['prompt_sha256'] or manifest['prompt_path'] != PROMPT_PATH:",'if False:','launch','LaunchTests.test_api_model_and_prompt_refusals'),
    ('output owner ignored','run_reviews.py','info.st_uid != os.getuid()','False','launch','LaunchTests.test_review_output_owner'),
    ('symlink output followed','run_reviews.py','os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK','os.O_RDONLY | os.O_NONBLOCK','launch','LaunchTests.test_symlink_review_is_invalid'),
    ('parent step rule removed','run_reviews.py',"parent in token.split('/')",'False','launch','LaunchTests.test_blindness_every_spelling'),
    ('absolute path rule removed','run_reviews.py',"candidate = (os.path.isabs(token)",'candidate = (False','launch','LaunchTests.test_blindness_every_spelling'),
    ('home path rule removed','run_reviews.py',"token.startswith((chr(126), home, brace_home))",'False','launch','LaunchTests.test_blindness_every_spelling'),
    ('blindness does not invalidate','review_record.py',"if env['blindness']['hits']:",'if False:','launch','LaunchTests.test_blindness_stream_makes_record_invalid'),
    ('limit no longer stops','run_reviews.py','        if limit:\n','        if False:\n','launch','LaunchTests.test_usage_limit_stops_retains_and_resumes'),
    ('only filter ignored','run_reviews.py','selected = [n for n in ids if n in only]','selected = list(ids)','launch','LaunchTests.test_only_and_existing_never_overwritten'),
    ('existing review rerun allowed','run_reviews.py',"if not read_json(path)['envelope']['ended_on_usage_limit']:",'if False:','launch','LaunchTests.test_only_and_existing_never_overwritten'),
    ('assistant model mismatch ignored','run_reviews.py','models + message_models if models else []','models','launch','LaunchTests.test_model_mismatch_invalid_and_synthetic_ignored'),
    ('model mismatch accepted','run_reviews.py','if not models or any(model != args.model for model in models):','if False:','launch','LaunchTests.test_model_mismatch_invalid_and_synthetic_ignored'),
    ('settings copy altered','run_reviews.py',"(kit / '.claude/settings.json').write_bytes(settings)","(kit / '.claude/settings.json').write_bytes(settings + b' ')",'launch','LaunchTests.test_envelope_and_command_are_code_owned'),
    ('created directory neutrality rule removed','run_reviews.py','if any(word in component.lower() for component in neutral_components for word in FORBIDDEN):','if False:','launch','LaunchTests.test_environment_and_neutral_parent_guard'),
    ('Claude environment retained','run_reviews.py',"k.startswith('CLAUDE') and k != 'CLAUDE_CODE_OAUTH_TOKEN'",'False','launch','LaunchTests.test_envelope_and_command_are_code_owned'),
    ('answer key in case allowed','build_cases.py',"if any(p.startswith('evals/review-faults/') for p in entries):",'if False:','build','BuildTests.test_answer_key_base_refused'),
    ('neutral id omits salt','build_cases.py',"(salt + case_id).encode('ascii')","case_id.encode('ascii')",'build','BuildTests.test_salt_changes_neutral_identifier'),
    ('output inside worktree allowed','build_cases.py',"if probe.returncode == 0 and probe.stdout.strip() == b'true':",'if False:','build','BuildTests.test_worktree_output_refused'),
    ('first run always true','score.py','first = previous is None','first = True','core','ScoreTests.test_rates_invalid_and_first_run_cold_twin'),
    ('answer hashes not checked','score.py',"if any(entry[field] != answer[field] for field in ('expected_sha256', 'plant_sha256')):",'if False:','core','ScoreTests.test_tamper_and_mixed_records'),
    ('mixed models accepted','score.py','if len(model_ids) > 1:','if False:','core','ScoreTests.test_tamper_and_mixed_records'),
    ('same uid record accepted','review_record.py',"if env['reviewer']['uid'] == env['producer']['uid']:",'if False:','core','ScoreTests.test_tamper_and_mixed_records'),
    ('record prompt mismatch accepted','review_record.py',"if manifest and env['reviewer']['prompt_sha256'] != manifest['prompt_sha256']:",'if False:','core','ScoreTests.test_tamper_and_mixed_records'),
    ('latest invalid attempt selected','score.py',"valid = [item for item in history if not item['invalid_reasons']]",'valid = history','core','ScoreTests.test_latest_valid_attempt_retains_all'),
    ('mask literal retained','score.py',"item = item.replace(literal, '<planted-secret>')",'item = item','core','ScoreTests.test_published_copy_masks_and_keeps_fields'),
    ('raw uid published','score.py',"if key in ('uid', 'host_digest'):","if key == 'host_digest':",'core','ScoreTests.test_published_copy_masks_and_keeps_fields'),
    ('zero denominator hidden','score.py',"text + ' uncomputable' if value['d'] == 0 else text",'text','core','ScoreTests.test_rates_invalid_and_first_run_cold_twin'),
]


EXPECTED_FAILURES = {
    'repository bytes nondeterministic': 'determinism digest mismatch:',
    'extra repository history': "b'3' != b'2'",
    'key enters case folder': 'key.json',
    'collision guard removed': 'FileExistsError: [Errno 17] File exists:',
    'nonapplying plant accepted': 'ValueError not raised',
    'settings copy altered': 'ValueError: settings copy differs',
    'latest invalid attempt selected': "TypeError: 'NoneType' object is not subscriptable",
    'answer interval shifted': 'answer match misses changed lines: P07',
}
FAULTS.append(('answer interval shifted','fixtures/plants/P07/expected.json',
               '"line_start": 73,\n    "line_end": 73',
               '"line_start": 57,\n    "line_end": 57',
               'build','BuildTests.test_plant_match_intervals_cover_changed_lines'))
FAULTS.append(('external input leak accepted','build_cases.py','        if leaks:',
               '        if False:','build','BuildTests.test_external_case_leak_refused'))

for label,needle in [('nested shell','bash -c'),('nested interpreter','python3 -c'),
                     ('brace home','{HOME}'),('variable parent','PWD'),('attached option','-C')]:
    FAULTS.append(('blindness ignores '+label,'run_reviews.py',
                   '                for token in tokens:',
                   '                if %r in text: tokens = []\n                for token in tokens:' % needle,
                   'launch','LaunchTests.test_blindness_every_spelling'))
FAULTS.append(('blindness ignores bare cd','run_reviews.py',
               'if bare_cd:','if False:',
               'launch','LaunchTests.test_blindness_every_spelling'))


# S1 carries R1's leak controls forward on item 15's committed surfaces.
for token in ('off-by-one', 'P01'):
    amend = "; build_cases.commit(folder/'repo', 'Clarify introduction', common.git(folder/'repo','rev-parse','HEAD~1').decode().strip())"
    for location, statement in [
            ('commit message', "build_cases.commit(folder/'repo', %r, common.git(folder/'repo','rev-parse','HEAD~1').decode().strip())" % token),
            ('root commit message', "parent=build_cases.commit(folder/'repo', %r); build_cases.commit(folder/'repo', 'Adjust comment', parent)" % token),
            ('changed file', "(folder/'repo'/'README.md').write_bytes((folder/'repo'/'README.md').read_bytes()+%r)" % token.encode('ascii') + amend),
            ('folder name', "renamed=folder.with_name(%r); folder.rename(renamed); folder=renamed" % token),
            ('manifest', "manifest_bytes+=%r" % token.encode('ascii')),
            ('plant diff added file', "(folder/'repo'/'addition.md').write_bytes(%r)" % token.encode('ascii') + amend),
            ('decoded tree name', "(folder/'repo'/%r).write_bytes(b'Harmless content\\n')" % token + amend)]:
        FAULTS.append(('added-byte leak in '+location+': '+token,
                       'tests/test_review_faults_build.py',
                       '        # Disposable-copy mutations inject each leak immediately before this check.',
                       '        '+statement, 'build', 'BuildTests.test_added_byte_leak_control'))
FAULTS.extend([
    ('changed base file wrongly exempt','case_sweep.py',
     "    yield 'added lines', b''.join(added_lines(diff))",
     "    yield 'added lines', b''",
     'build','BuildTests.test_base_exemption_is_byte_identity_at_same_path'),
    ('renamed base blob wrongly exempt','case_sweep.py',
     'if relative not in baseline:', 'if relative not in baseline and data not in baseline.values():',
     'build','BuildTests.test_base_exemption_is_byte_identity_at_same_path'),
    ('unchanged lines wrongly swept','case_sweep.py',
     "yield label, b''.join(blobs[oid])", 'yield label, data',
     'build','BuildTests.test_added_byte_leak_control'),
])
GREEN_CONTROLS = [
    ('unchanged line of changed file: '+token, 'tests/test_review_faults_build.py',
     '        # Disposable green controls add a token before the base commit.',
     "        inherited += %r" % (token+'\n').encode('ascii'),
     'build', 'BuildTests.test_added_byte_leak_control')
    for token in ('off-by-one', 'P01')
]


class FaultTests(unittest.TestCase):
    def test_every_guard_fault_is_red(self):
        for label,relative,old,new,module,case in FAULTS + GREEN_CONTROLS:
            with self.subTest(fault=label),tempfile.TemporaryDirectory(prefix='t-') as temp:
                scratch=Path(temp).resolve()
                root=scratch/'source'
                root.mkdir()
                runtime=scratch/'runtime'
                runtime.mkdir()
                target=root/'evals/review-faults'
                target.parent.mkdir(parents=True)
                shutil.copytree(str(REPO/'evals/review-faults'),str(target),
                                ignore=shutil.ignore_patterns('__pycache__','runs'))
                (root/'.git').symlink_to(REPO/'.git',target_is_directory=True)
                prompt=root/'gars/_references/prompts/review_faults_code.md'
                prompt.parent.mkdir(parents=True)
                shutil.copyfile(str(REPO/'gars/_references/prompts/review_faults_code.md'),str(prompt))
                (root/'tests').mkdir()
                (root/'scripts').mkdir()
                shutil.copyfile(str(REPO/'scripts/release_check.py'),str(root/'scripts/release_check.py'))
                name='test_review_faults_'+module+'.py'
                shutil.copyfile(str(REPO/'tests'/name),str(root/'tests'/name))
                path=root/relative if relative.startswith('tests/') else target/relative
                original=path.read_text()
                self.assertIn(old,original,label)
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
                # Absolute scratch locations are built at runtime, never source literals.
                for key in ('TMPDIR','TEMP','TMP'):
                    env[key]=str(runtime)
                def execute():
                    proc=subprocess.run([sys.executable,str(root/'tests'/name),case],
                                        cwd=str(REPO),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                        timeout=180)
                    return proc, (proc.stdout+proc.stderr).decode('utf-8','replace')
                baseline,baseline_output=execute()
                self.assertEqual(baseline.returncode,0,'unfaulted control: '+label+'\n'+baseline_output)
                self.assertIn('OK',baseline_output)
                path.write_text(original.replace(old,new,1))
                proc,output=execute()
                self.assertIn(case.split('.')[1],output)
                self.assertNotIn('ModuleNotFoundError',output)
                if (label,relative,old,new,module,case) in GREEN_CONTROLS:
                    self.assertEqual(proc.returncode,0,output)
                    self.assertIn('OK',output)
                    print('exemption green: '+label)
                else:
                    self.assertNotEqual(proc.returncode,0,output)
                    self.assertIn('FAILED (',output)
                    if label not in ('collision guard removed','settings copy altered','latest invalid attempt selected'):
                        self.assertNotIn('ERROR:',output)
                    expected=EXPECTED_FAILURES.get(label, 'AssertionError')
                    self.assertIn(expected,output, 'wrong failure for '+label+'\n'+output)
                    print('fault red: '+label)


if __name__=='__main__':
    unittest.main(verbosity=2)
