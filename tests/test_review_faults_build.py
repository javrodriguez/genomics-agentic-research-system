"""Case construction, fixture applicability and history isolation without a reviewer."""
import io
import json
import shutil
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path
from unittest import mock

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'evals/review-faults'))
import build_cases
import common
from testing import temporary, base_blobs, case_leaks


class BuildTests(unittest.TestCase):
    def subset(self,root):
        answers=root/'answers'
        answers.mkdir()
        shutil.copytree(str(common.HERE/'fixtures/clean/C03'),str(answers/'C03'))
        return answers

    def test_determinism_history_and_private_key(self):
        root=temporary(self)
        answers=self.subset(root)
        salt='a'*32
        first=root/'a'
        second=root/'b'
        key,manifest=build_cases.build(first,[answers],salt)
        build_cases.build(second,[answers],salt)
        def snapshot(path):
            return {str(p.relative_to(path)):p.read_bytes() for p in path.rglob('*') if p.is_file()}
        self.assertEqual(snapshot(first),snapshot(second))
        self.assertEqual(set(key),{'run_salt','cases'})
        self.assertNotIn(salt,(first/'manifest.json').read_text())
        self.assertEqual(set(manifest),{'cases','base_sha','prompt_path','prompt_sha256','harness_commit'})
        for neutral in manifest['cases']:
            folder=first/'cases'/neutral
            self.assertEqual([p.name for p in folder.iterdir()],['repo'])
            repo=folder/'repo'
            self.assertEqual(common.git(repo,'rev-list','--count','HEAD').strip(),b'2')
            self.assertEqual(common.git(repo,'rev-list','--parents','HEAD~1').decode().strip().count(' '),0)
            self.assertEqual(common.git(repo,'rev-parse','HEAD~1^{tree}'),common.git(REPO,'rev-parse',common.BASE_SHA+'^{tree}'))
            self.assertEqual(common.git(repo,'log','--format=%an <%ae>|%cn <%ce>').decode().splitlines(),
                             ['GARS producer <producer@example.invalid>|GARS producer <producer@example.invalid>']*2)
            self.assertFalse((repo/'evals/review-faults').exists())
            self.assertFalse(list(folder.rglob('key.json')))
            self.assertRegex(neutral,'^[0-9a-f]{12}$')
            for cid in key['cases'].values():
                self.assertNotIn(cid['id'],neutral)
        for cid in key['cases'].values():
            self.assertNotIn(cid['id'],(first/'manifest.json').read_text())
        self.assertNotEqual(build_cases.neutral_id(salt,'C03'),build_cases.neutral_id('b'*32,'C03'))

    def test_every_fixture_applies_to_base_archive(self):
        root=temporary(self)
        archive=build_cases.base_archive(REPO,common.BASE_SHA)
        cases=common.load_cases([common.HERE/'fixtures'])
        self.assertEqual(len(cases),12)
        self.assertEqual(sum(c['expected']['kind']=='clean' for c in cases.values()),5)
        planted={c['expected']['class'] for c in cases.values() if c['expected']['kind']=='plant'}
        self.assertEqual(planted,set(common.CLASSES)-set(common.SEALED))
        for cid,case in cases.items():
            tree=root/cid
            tree.mkdir()
            build_cases.export(archive,tree)
            patch=(case['path']/'plant.diff').read_bytes()
            common.git(tree,'apply','--check','-',input=patch)
            common.git(tree,'apply','-',input=patch)
            if case['expected']['kind']=='plant':
                expected=case['expected']
                for line in patch.decode().splitlines():
                    if line.startswith('+') and '#' in line and not line.startswith('+++'):
                        self.assertNotIn(expected['class'],line)
                self.assertNotIn(expected['class'],expected['commit_message'])
            shutil.rmtree(str(tree))
        print('fixtures: git apply --check passed for 12/12 against base archive')

    def test_build_refusals(self):
        root=temporary(self)
        answers=self.subset(root)
        with self.assertRaisesRegex(ValueError,'inside a git work tree'):
            build_cases.build(REPO/'should-not-exist',[answers])
        (root/'exists').mkdir()
        with self.assertRaisesRegex(ValueError,'already exists'):
            build_cases.build(root/'exists',[answers])
        shutil.copytree(str(common.HERE/'fixtures/clean/C02'),str(answers/'C02'))
        with mock.patch.object(build_cases,'neutral_id',return_value='a'*12):
            with self.assertRaisesRegex(ValueError,'collision'):
                build_cases.build(root/'collision',[answers])
        shutil.rmtree(str(answers/'C02'))
        (answers/'C03/plant.diff').write_text('not a patch\n')
        with self.assertRaisesRegex(ValueError,'plant does not apply'):
            build_cases.build(root/'bad',[answers])

    def test_answer_key_base_refused(self):
        root=temporary(self)
        source=root/'s'
        source.mkdir()
        common.git(source,'init','--quiet','--template=')
        common.git(source,'symbolic-ref','HEAD','refs/heads/main')
        (source/'evals/review-faults').mkdir(parents=True)
        (source/'evals/review-faults/answer.json').write_text('{}')
        commit=build_cases.commit(source,'Initial source snapshot')
        with self.assertRaisesRegex(ValueError,'answer-key-in-case'):
            build_cases.base_archive(source,commit)

    def test_salt_changes_neutral_identifier(self):
        self.assertNotEqual(build_cases.neutral_id('a'*32,'P01'),build_cases.neutral_id('b'*32,'P01'))

    def test_worktree_output_refused(self):
        root=temporary(self)
        common.git(root,'init','--quiet','--template=')
        with self.assertRaisesRegex(ValueError,'inside a git work tree'):
            build_cases.refuse_worktree(root/'out')

    def forbidden_tokens(self):
        cases=common.load_cases([common.HERE/'fixtures'])
        return list(common.CLASSES)+list(cases)+[
            str(case['path'].relative_to(REPO)) for case in cases.values()]

    def assert_case_clear(self, folder, manifest, patch, baseline):
        self.assertEqual(case_leaks(folder,manifest,patch,baseline,
                                    self.forbidden_tokens()),[])

    def test_added_case_bytes_sweep(self):
        root=temporary(self)
        output=root/'out'
        key,manifest=build_cases.build(output,run_salt='a'*32)
        baseline=base_blobs()
        cases=common.load_cases([common.HERE/'fixtures'])
        manifest_bytes=(output/'manifest.json').read_bytes()
        leaks=[]
        for neutral in manifest['cases']:
            cid=key['cases'][neutral]['id']
            leaks.extend((cid,label,token) for label,token in case_leaks(
                output/'cases'/neutral,manifest_bytes,
                (cases[cid]['path']/'plant.diff').read_bytes(),baseline,self.forbidden_tokens()))
        self.assertEqual(leaks,[])
        print('added case-byte sweep: 12/12 clear; only identical base blobs exempt')

    def sweep_fixture(self):
        root=temporary(self)
        folder=root/('a'*12)
        repo=folder/'repo'
        repo.mkdir(parents=True)
        common.git(repo,'init','--quiet','--template=')
        common.git(repo,'symbolic-ref','HEAD','refs/heads/main')
        spec='docs/specs/source.md'
        (repo/spec).parent.mkdir(parents=True)
        inherited=b'off-by-one race\n'
        (repo/spec).write_bytes(inherited)
        (repo/'README.md').write_bytes(b'Before\n')
        baseline={spec:inherited,'README.md':b'Before\n'}
        parent=build_cases.commit(repo,'Initial source snapshot')
        (repo/'README.md').write_bytes(b'After\n')
        build_cases.commit(repo,'Clarify introduction',parent)
        patch=common.git(repo,'diff','HEAD~1','HEAD')
        return folder,b'{}',patch,baseline,spec

    def test_base_exemption_is_byte_identity_at_same_path(self):
        folder,manifest_bytes,patch,baseline,spec=self.sweep_fixture()
        repo=folder/'repo'
        inherited=(repo/spec).read_bytes()
        self.assertIn(b'off-by-one',inherited)
        self.assertEqual(inherited,baseline[spec])
        self.assert_case_clear(folder,manifest_bytes,patch,baseline)
        # The same filename is not exempt after even a harmless byte changes.
        (repo/spec).write_bytes(inherited+b'\n')
        self.assertIn(('file '+spec,'off-by-one'),
                      case_leaks(folder,manifest_bytes,patch,baseline,self.forbidden_tokens()))
        (repo/spec).write_bytes(inherited)
        # Identical contents under a new name have no base blob at that path.
        (repo/'copy.md').write_bytes(inherited)
        self.assertIn(('file copy.md','off-by-one'),
                      case_leaks(folder,manifest_bytes,patch,baseline,self.forbidden_tokens()))
        (repo/'copy.md').unlink()
        self.assert_case_clear(folder,manifest_bytes,patch,baseline)

    def test_added_byte_leak_control(self):
        folder,manifest_bytes,patch,baseline,spec=self.sweep_fixture()
        # Disposable-copy mutations inject each leak immediately before this check.
        self.assert_case_clear(folder,manifest_bytes,patch,baseline)


if __name__=='__main__':
    unittest.main(verbosity=2)
