"""Real subprocess stub exercises the reference launch boundary, without a model."""
import io
import json
import os
import stat
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'evals/review-faults'))
import common
import review_record
import run_reviews
from testing import launch_context, launcher_fixture, stub, temporary


class LaunchTests(unittest.TestCase):
    def test_envelope_and_command_are_code_owned(self):
        root,args,manifest=launcher_fixture(self,1)
        events=[{'type':'system','subtype':'init','model':'stub-model',
                 'envelope':{'reviewer':{'uid':0},'blindness':{'hits':0},
                             'sandbox_settings_sha256':'0'*64}}]
        stub(root,events=events)
        settings=root/'settings.json'
        settings.write_text('{"permissions":{}}\n')
        args.settings=str(settings)
        with launch_context(root), mock.patch.object(run_reviews, 'blindness', wraps=run_reviews.blindness) as scan:
            self.assertEqual(run_reviews.run(args),0)
        neutral=manifest['cases'][0]
        record=common.read_json(Path(args.records)/(neutral+'.record.json'))
        self.assertEqual(review_record.invalid_reasons(record,manifest),[])
        envelope=record['envelope']
        self.assertEqual(envelope['sandbox_settings_sha256'],common.sha256(settings.read_bytes()))
        self.assertEqual(envelope['reviewer']['uid'],os.getuid())
        self.assertNotEqual(envelope['reviewer']['uid'],envelope['producer']['uid'])
        self.assertEqual(envelope['reviewer']['model_id'],'stub-model')
        self.assertEqual(envelope['reviewer']['prompt_sha256'],manifest['prompt_sha256'])
        kit=Path(args.kits_root)/neutral
        self.assertEqual((kit/'.claude/settings.json').read_bytes(),settings.read_bytes())
        invocation=common.read_json(kit/'invocation.json')
        session=invocation['argv'][invocation['argv'].index('--session-id')+1]
        self.assertEqual(scan.call_args[0][1:],(kit,session))
        self.assertEqual(envelope['reviewer']['session_id'],session)
        self.assertEqual(invocation['stdin'],'')
        for flag,value in [('--model','stub-model'),('--permission-mode','auto'),
                           ('--permission-prompts','none'),('--setting-sources','project,local'),
                           ('--output-format','stream-json')]:
            index=invocation['argv'].index(flag)
            self.assertEqual(invocation['argv'][index+1],value)
        self.assertIn('--strict-mcp-config',invocation['argv'])
        for key in ('CLAUDE_POISON','ANTHROPIC_POISON','TMP_POISON'):
            self.assertNotIn(key,invocation['env'])
        for key in ('TMPDIR','TEMP','TMP'):
            self.assertEqual(invocation['env'][key],str(kit/'tmp'))
        self.assertEqual(common.git(kit/'repo','remote'),b'')
        for path in (kit/'repo/.git/logs').rglob('*'):
            if path.is_file():
                self.assertNotIn(str(Path(args.cases)).encode(),path.read_bytes())
        self.assertFalse(any(word in part.lower() for part in kit.relative_to(Path(args.kits_root)).parts for word in run_reviews.FORBIDDEN))

    def test_identity_refusals(self):
        uid=os.getuid()
        with mock.patch.object(run_reviews.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=uid,pw_name='synthetic')):
            with self.assertRaisesRegex(ValueError,'uid must differ'):
                run_reviews.launch_identity('synthetic')
        with mock.patch.object(run_reviews.pwd,'getpwnam',side_effect=KeyError('missing')):
            with self.assertRaisesRegex(ValueError,'does not resolve'):
                run_reviews.launch_identity('synthetic')
        with mock.patch.object(run_reviews.os,'getuid',return_value=0):
            with self.assertRaisesRegex(ValueError,'privileged'):
                run_reviews.launch_identity('synthetic')

    def test_api_model_and_prompt_refusals(self):
        root,args,manifest=launcher_fixture(self,1)
        stub(root)
        with launch_context(root):
            with mock.patch.dict(os.environ,{'ANTHROPIC_API_KEY':'PLACEHOLDER_ONLY'}):
                with self.assertRaisesRegex(ValueError,'ANTHROPIC_API_KEY'):
                    run_reviews.run(args)
            original=args.model
            args.model=''
            with self.assertRaisesRegex(ValueError,'model required'):
                run_reviews.run(args)
            args.model=original
            Path(args.prompt).write_text('changed prompt')
            with self.assertRaisesRegex(ValueError,'prompt does not match'):
                run_reviews.run(args)
        self.assertFalse(Path(args.kits_root).exists())

    def test_settings_required_before_launch(self):
        root,args,manifest=launcher_fixture(self,1)
        stub(root)
        args.settings=None
        with launch_context(root), mock.patch.object(run_reviews.subprocess, 'check_output') as launch:
            with self.assertRaisesRegex(ValueError,'sandbox settings required'):
                run_reviews.run(args)
            launch.assert_not_called()
        self.assertFalse(Path(args.kits_root).exists())
        argv=[]
        for name in ('cases','manifest','prompt','kits-root','records','model','producer-account','login-entry'):
            argv.extend(['--'+name,str(getattr(args,name.replace('-','_')))])
        with mock.patch('sys.stderr',io.StringIO()), mock.patch.object(run_reviews,'run') as run:
            with self.assertRaises(SystemExit) as refused:
                run_reviews.main(argv)
            self.assertEqual(refused.exception.code,2)
            run.assert_not_called()

    def test_review_output_owner(self):
        root=temporary(self)
        path=root/'review.json'
        path.write_text('{"verdict":"APPROVE","findings":[]}')
        info=SimpleNamespace(st_mode=stat.S_IFREG | 0o600,st_uid=os.getuid()+1)
        with mock.patch.object(run_reviews.os,'fstat',return_value=info):
            with self.assertRaisesRegex(ValueError,'owned by reviewer'):
                run_reviews.safe_review(path)

    def test_symlink_review_is_invalid(self):
        root,args,manifest=launcher_fixture(self,1)
        stub(root,symlink=True)
        with launch_context(root):
            run_reviews.run(args)
        path=next(Path(args.records).glob('*.record.json'))
        self.assertTrue(review_record.invalid_reasons(common.read_json(path),manifest))

    def test_blindness_every_spelling(self):
        root=temporary(self)
        kit=root/'k'
        kit.mkdir()
        parent=chr(46)*2
        home='$'+'HOME'
        bad=[os.path.join(os.sep,'outside','file'), chr(126)+os.sep+'file',
             home+os.sep+'file',os.path.join(parent,parent,'file')]
        outside_path=os.path.join(os.sep,'outside','file')
        bad += ["bash -c 'cat " + outside_path + "'",
                'python3 -c "print(open(' + repr(outside_path) + ').read())"',
                ('$'+'{HOME}')+os.sep+'file',
                os.path.join('$'+'PWD',parent,'file'), '-C'+outside_path,
                '-C'+os.path.join(parent,'file'), '-C'+home+os.sep+'file',
                chr(92)+os.path.join(parent,'file')]
        good=['2>/dev/null','/usr/bin/env',str(kit/'file'),'repo/module.py']
        good += ['--basetemp=tmp/x', '--git-dir=repo/.git',
                 "awk -F '"+os.sep+"' '{print $1}' repo/input.txt",
                 "cut -d '"+os.sep+"' -f 1 repo/input.txt",
                 'python3 -c "print(8 '+os.sep*2+' 2)"',
                 os.path.join('$'+'{PWD}','repo','file')]
        for token in bad+good:
            command=token if token.startswith(('awk ', 'cut ', 'python3 ', 'bash ')) else 'cat '+token
            events=[{'type':'assistant','message':{'content':[{'type':'tool_use','input':{'command':command}}]}}]
            result=run_reviews.blindness(events,kit)
            self.assertEqual(result['calls'],1)
            self.assertEqual(result['hits'],1 if token in bad else 0,token)
        for command in ('cd && cat secret', '  cd', "bash -c 'cd && cat secret'", "cat 'unterminated",
                        'echo ready\ncd\ncat secret', '( cd; cat secret )',
                        '{ cd; cat secret; }', 'if true; then cd; cat secret; fi',
                        'for x in y; do cd; cat secret; done', 'if false; then :; else cd; fi',
                        'builtin cd; cat secret', 'command cd; cat secret',
                        'cd -- && cat secret', 'cd -L; cat secret', 'cd -P; cat secret',
                        'cd -L -P --; cat secret', 'eval cd; cat secret',
                        'exec cd; cat secret', 'time cd; cat secret',
                        'eval cd --; cat secret',
                        'if cd; then cat secret; fi', chr(92)+'cd; cat secret',
                        'time -p cd; cat secret', 'command -- cd; cat secret',
                        'env -- cd -P; cat secret', 'timeout 5 cd --; cat secret',
                        'cd 2>/dev/null; cat secret', 'cd -P 2>/dev/null; cat secret',
                        'cd 2>/dev/null 3>/dev/null; cat secret',
                        'cd 2>&1; cat secret',
                        'bash -lc "cd; cat secret"',
                        os.path.join(os.sep,'bin','bash')+' -c "cd; cat secret"',
                        'cat '+('$'+'{HOME%/}')+os.sep+'file',
                        'cat '+os.path.join('$'+'{PWD%/*}',parent,'file')):
            self.assertEqual(run_reviews.blindness([{'type':'tool_use','input':{'command':command}}],kit)['hits'],1,command)
        root_commands = ['cd '+os.sep+' && cat relative/file',
                         'cd $'+repr(os.sep)+'; cat relative/file',
                         'cd $"'+os.sep+'"; cat relative/file',
                         'ls '+os.sep, 'ls -d '+os.sep, 'cat awk '+os.sep, 'find '+os.sep+' -name sample',
                         'grep -R pattern '+os.sep,
                         'ls "'+os.sep+'"', 'ls '+os.sep*2,
                         "bash -c 'ls "+os.sep+"'",
                         'git -C'+os.sep+' status',
                         'git --git-dir='+os.sep+' status',
                         'awk -F '+os.sep+" '{print $1}' "+os.sep,
                         'awk -f '+os.sep, 'sed -f '+os.sep,
                         'awk -f repo/program '+os.sep,
                         'sed --file=repo/program '+os.sep,
                         'awk --source=program '+os.sep,
                         'awk -e program '+os.sep, 'awk '+repr(os.sep)+' repo/input.txt',
                         'echo "$('+'ls '+os.sep+')"',
                         'env bash -c "ls '+os.sep+'"',
                         'bash -lc "ls '+os.sep+'"',
                         'timeout 5 bash -c "ls '+os.sep+'"',
                         'CDPATH='+os.sep+' cd etc',
                         'x='+os.sep+'; cd $x',
                         'printf "prefix '+os.sep+' suffix"']
        for command in root_commands:
            with self.subTest(command=command):
                event={'type':'tool_use','input':{'command':command}}
                self.assertEqual(run_reviews.blindness([event],kit)['hits'],1,command)
        command='HOME='+os.sep+' cd'
        self.assertEqual(run_reviews.blindness([{'type':'tool_use','input':{'command':command}}],kit)['hits'],2)
        for field in ('file_path','path','notebook_path','directory','input_path'):
            event={'type':'tool_use','input':{field:os.sep}}
            self.assertEqual(run_reviews.blindness([event],kit)['hits'],1)
        for command in ['cd -- repo && cat module.py', 'cd -L repo',
                        'cd -P repo', 'eval cd repo', 'exec cd repo', 'time cd repo',
                        'if cd repo; then cat module.py; fi', chr(92)+'cd repo',
                        'time -p cd repo', 'command -- cd repo',
                        'env -- cd repo', 'timeout 5 cd repo',
                        'cd repo 2>/dev/null', 'cd 2>/dev/null repo',
                        'cd -P 2>/dev/null repo', 'cd repo 2>&1',
                        'bash -lc "cd repo; cat module.py"',
                        os.path.join(os.sep,'bin','bash')+' -c "cd repo; cat module.py"',
                        'cd $'+repr('repo')+'; cat module.py',
                        'cd $"repo"; cat module.py',
                        'cut --delimiter='+os.sep+' -f 1 repo/input.txt',
                        'cut --delimiter '+os.sep+' -f 1 repo/input.txt',
                        'awk --field-separator='+os.sep+" '{print $1}' repo/input.txt",
                        'awk --field-separator '+os.sep+" '{print $1}' repo/input.txt",
                        'awk -F'+os.sep+" '{print $1}' repo/input.txt",
                        'cut -d'+os.sep+' -f 1 repo/input.txt',
                        'python3 -c "print(8 '+os.sep+' 2)"',
                        'python3 -c "'+os.sep+'"']:
            event={'type':'tool_use','input':{'command':command}}
            self.assertEqual(run_reviews.blindness([event],kit)['hits'],0,command)
        # Item 20(b)(iii): prose is not a command; named paths still get rule (i).
        for field,text in [('description','Compare old '+os.sep+' new files'),
                           ('pattern',os.sep),('prompt','Split on '+os.sep+' please')]:
            for value,expected in [(text,0),(outside_path,1),('repo/module.py',0)]:
                event={'type':'tool_use','input':{field:value}}
                self.assertEqual(run_reviews.blindness([event],kit)['hits'],expected,field)
        # Item 20(c): interpreter program text is a sandbox responsibility.
        for interpreter,option,program in [
                ('python3','-c',"import os;os.chdir('"+os.sep+"');print(os.listdir())"),
                ('perl','-e',"chdir('"+os.sep+"')"),
                ('ruby','-e',"Dir.chdir('"+os.sep+"')"),
                ('node','-e',"process.chdir('"+os.sep+"')")]:
            event={'type':'tool_use','input':{'command':interpreter+' '+option+' "'+program+'"'}}
            self.assertEqual(run_reviews.blindness([event],kit)['hits'],0)
        for field in ('content','old_string','new_string','old_text','new_text'):
            event={'type':'tool_use','input':{'file_path':'review.json',field:os.sep}}
            self.assertEqual(run_reviews.blindness([event],kit)['hits'],0,field)
        prose='A slash '+os.sep+' or division '+os.sep*2+' is ordinary text.'
        body=json.dumps({'verdict':'APPROVE_WITH_CHANGES','findings':[
            {'summary':prose,'evidence':prose}]})
        self.assertEqual(run_reviews.blindness([{'type':'tool_use','input':{
            'file_path':'review.json','content':body}}],kit)['hits'],0)
        for option in ('--git-dir=', '-C'):
            command='git '+option+outside_path+' status'
            self.assertGreater(run_reviews.blindness([{'type':'tool_use','input':{
                'command':command}}],kit)['hits'],0,command)
        outside=root/'outside'
        outside.mkdir()
        (kit/'link').symlink_to(outside,target_is_directory=True)
        token=str(kit/'link'/'file')
        self.assertEqual(run_reviews.blindness([{'type':'tool_use','input':{'path':token}}],kit)['hits'],1)

    def test_session_output_store_boundary(self):
        root=temporary(self)
        kit=root/'k_9.with space'/'a1-b2'
        kit.mkdir(parents=True)
        home=root/'h'
        projects=home/'.claude'/'projects'
        session='12345678-1234-4234-8234-123456789abc'
        # Independent character-by-character oracle against the runtime kit path.
        letters='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
        project=''.join(c if c in letters else '-' for c in str(kit))
        store=projects/project/session/'tool-results'
        store.mkdir(parents=True)
        (store/'link').symlink_to(root,target_is_directory=True)
        outside=[projects/project/(session+'.jsonl'),
                 projects/project/'other-session'/'tool-results'/'output.txt',
                 projects/(project+'-other')/session/'tool-results'/'output.txt',
                 projects/project/'memory'/'entry.md',store/'link'/'private.txt',
                 store/(chr(46)*2)/'transcript.jsonl']
        with mock.patch.object(run_reviews.pwd,'getpwuid',return_value=SimpleNamespace(pw_dir=str(home))):
            self.assertEqual(run_reviews.session_output_store(kit,session),store)
            for path in [store/'output.txt',store/'nested'/'output.txt']+outside:
                event={'type':'tool_use','input':{'file_path':str(path)}}
                hits=run_reviews.blindness([event],kit,session)['hits']
                self.assertEqual(hits,1 if path in outside else 0,str(path.relative_to(root)))
            event={'type':'tool_use','input':{'file_path':str(store/'output.txt')}}
            self.assertEqual(run_reviews.blindness([event],kit)['hits'],1)

    def test_blindness_stream_makes_record_invalid(self):
        parent=chr(46)*2
        for token in (os.path.join(os.sep,'outside','file'),chr(126)+os.sep+'file',
                      ('$'+'HOME')+os.sep+'file',os.path.join(parent,parent,'file'),
                      os.sep, 'x; cd '+os.sep+' && cat relative/file',
                      'x; ls '+os.sep, 'x; find '+os.sep+' -name sample',
                      'x; cd -- && cat secret', 'x; eval cd; cat secret',
                      'x; cd 2>/dev/null; cat secret',
                      'x; cd $'+repr(os.sep)+'; cat relative/file',
                      'x; cd $"'+os.sep+'"; cat relative/file',
                      'x; bash -lc "cd; cat secret"',
                      'x; '+os.path.join(os.sep,'bin','bash')+' -c "cd; cat secret"'):
            root,args,manifest=launcher_fixture(self,1)
            events=[{'type':'system','subtype':'init','model':'stub-model'},
                    {'type':'assistant','message':{'content':[{'type':'tool_use','input':{'command':'cat '+token}}]}}]
            stub(root,events=events)
            with launch_context(root):
                run_reviews.run(args)
            record=common.read_json(next(Path(args.records).glob('*.record.json')))
            self.assertEqual(record['envelope']['blindness']['hits'],1)
            self.assertIn('blindness hit',review_record.invalid_reasons(record,manifest))

    def test_usage_limit_stops_retains_and_resumes(self):
        root,args,manifest=launcher_fixture(self)
        events=[{'type':'system','subtype':'init','model':'stub-model'},
                {'type':'assistant','message':{'model':'<synthetic>','content':[{'type':'text',
                    'text':"You've hit your session limit. Try later."}]}}]
        stub(root,events=events)
        output=io.StringIO()
        with launch_context(root),redirect_stdout(output):
            self.assertEqual(run_reviews.run(args),0)
        files=list(Path(args.records).glob('*.record.json'))
        self.assertEqual(len(files),1)
        self.assertIn('remaining: '+manifest['cases'][1],output.getvalue())
        first=files[0].read_bytes()
        item=common.read_json(files[0])
        self.assertTrue(item['envelope']['ended_on_usage_limit'])
        self.assertIn('usage limit',review_record.invalid_reasons(item,manifest))
        stub(root)
        args.kits_root=str(root/'k2')
        args.only=manifest['cases'][0]
        args.login_entry=2
        with launch_context(root):
            run_reviews.run(args)
        self.assertEqual(files[0].read_bytes(),first)
        attempt=Path(args.records)/(manifest['cases'][0]+'.attempt2.record.json')
        self.assertEqual(common.read_json(attempt)['envelope']['reviewer']['attempt'],2)
        self.assertTrue((Path(args.records)/(manifest['cases'][0]+'.attempt2.stream.jsonl')).exists())
        for text in ("You've hit your limit",'You\u2019ve hit your weekly limit','Claude usage limit reached.'):
            self.assertTrue(run_reviews.stream_facts([{'text':text}], '')[1])

    def test_only_and_existing_never_overwritten(self):
        root,args,manifest=launcher_fixture(self)
        stub(root)
        args.only=manifest['cases'][1]
        with launch_context(root):
            run_reviews.run(args)
            records=list(Path(args.records).glob('*.record.json'))
            self.assertEqual([p.name for p in records],[args.only+'.record.json'])
            original=records[0].read_bytes()
            args.kits_root=str(root/'k2')
            with self.assertRaisesRegex(ValueError,'never overwritten'):
                run_reviews.run(args)
            self.assertEqual(records[0].read_bytes(),original)

    def test_model_mismatch_invalid_and_synthetic_ignored(self):
        for model,message_model,valid in [('another-model','<synthetic>',False),
                                          ('stub-model','<synthetic>',True),
                                          ('stub-model','another-model',False)]:
            root,args,manifest=launcher_fixture(self,1)
            events=[{'type':'system','subtype':'init','model':model},
                    {'type':'assistant','message':{'model':message_model,'content':[]}}]
            stub(root,events=events)
            with launch_context(root):
                run_reviews.run(args)
            record=common.read_json(next(Path(args.records).glob('*.record.json')))
            self.assertEqual(not review_record.invalid_reasons(record,manifest),valid)
            self.assertEqual(record['envelope']['reviewer']['model_id'],model)

    def test_environment_and_neutral_parent_guard(self):
        root,args,manifest=launcher_fixture(self,1)
        stub(root)
        args.kits_root=str(root/'review-folder')
        with launch_context(root):
            self.assertEqual(run_reviews.run(args),0)
        args.kits_root=str(root/'review-folder2')
        args.records=str(root/'r2')
        with launch_context(root), mock.patch.object(run_reviews,'FORBIDDEN',('repo',)):
            with self.assertRaisesRegex(ValueError,'neutral path'):
                run_reviews.run(args)
        with mock.patch.dict(os.environ,{'CLAUDE_CODE_OAUTH_TOKEN':'PLACEHOLDER_ONLY',
                                        'CLAUDE_OTHER':'remove','ANTHROPIC_OTHER':'remove','TEMP_OTHER':'remove'},clear=True):
            cleaned=run_reviews.clean_environment(root)
        self.assertEqual(cleaned['CLAUDE_CODE_OAUTH_TOKEN'],'PLACEHOLDER_ONLY')
        self.assertNotIn('CLAUDE_OTHER',cleaned)
        self.assertNotIn('ANTHROPIC_OTHER',cleaned)
        self.assertNotIn('TEMP_OTHER',cleaned)


if __name__=='__main__':
    unittest.main(verbosity=2)
