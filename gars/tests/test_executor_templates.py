"""0251: one protected executor template per descriptor `nextflow_config` name.

`check_groovy` compared every executor config with `nextflow.slurm.config`, whatever the
descriptor named, so an AWS Batch venue could not pass preflight (the launch pad's refusal at
37a8d94). It now compares with `_templates/config/<the descriptor's nextflow_config name>`.
That WIDENS a guard, so most of this module is about what must still be refused: any other
grammar, any name that is not a bare template name, a symlinked template, and a config the
check reads that is not the one the wrapper passes with -c.
"""
import hashlib
import os
import shlex
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, REPO
import wrapperlib as wl

TEMPLATES = GARS / '_templates' / 'config'
SLURM = TEMPLATES / 'nextflow.slurm.config'
AWSBATCH = TEMPLATES / 'nextflow.awsbatch.config'
FIXTURE = GARS / 'tests' / 'fixtures' / 'executor' / 'nextflow.awsbatch.d-generator.config'
REFUSED = 'R-098/§9.6: unregistered Groovy grammar; use the seeded executor config'
NO_TEMPLATE = 'names no protected executor template'
NOT_IN_CONFIG = "is not a file directly in the project's _config/"
BARE = 'R-075: nextflow_config must be a bare file name in _config/'
# The recording rig's descriptor, as the pad's generator writes it with --head local.
RIG = 'name: local\nnextflow_config: nextflow.awsbatch.config\nnextflow_profile: ""\n'
EVIL_LINE = '\nprocess.beforeScript = "touch _system/x"\n'


def details(fails):
    return [f['detail'] for f in fails]


class ExecutorTemplateTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='gars-executor-templates-')).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def project(self, descriptor=RIG, root=None):
        self.count += 1
        project = (root or self.tmp) / ('p%d' % self.count)
        (project / '_config').mkdir(parents=True)
        if descriptor is not None:
            (project / '_config' / 'executor.yaml').write_text(descriptor, encoding='utf-8')
        return project

    def check(self, project, text=None):
        """Preflight exactly as every nf-core wrapper calls it, on the path it passes with -c."""
        passed = wl.ex.nextflow_config_path(project) or project / '_config' / 'nextflow.slurm.config'
        if text is not None:
            passed.parent.mkdir(parents=True, exist_ok=True)
            passed.write_text(text, encoding='utf-8')
        fails = []
        wl.check_executor_config(passed, fails)
        return details(fails)

    # -- admitted --------------------------------------------------------------------------

    def test_01_the_template_itself_is_admitted(self):
        """Fails while check_groovy compares every config with the slurm template."""
        self.assertEqual(self.check(self.project(), AWSBATCH.read_text(encoding='utf-8')), [])

    def test_02_the_generator_shape_is_admitted_for_a_take_and_a_rehearsal(self):
        """The D generator's shape (other comments, spacing and site values) passes, and a
        rehearsal differs from the take only in the one job-tag value."""
        take = FIXTURE.read_text(encoding='utf-8')
        rehearsal = take.replace("goal: 'gars-launch-pad'", "goal: 'gars-launch-pad-rehearsal'")
        changed = [(a, b) for a, b in zip(take.splitlines(), rehearsal.splitlines()) if a != b]
        self.assertEqual(len(changed), 1, changed)
        for text in (take, rehearsal):
            self.assertEqual(self.check(self.project(), text), [])

    def test_03_a_new_site_value_passes_and_an_unsafe_one_is_refused(self):
        """Single-quoted values are site values under R-075's charset, nothing more."""
        take = FIXTURE.read_text(encoding='utf-8')
        self.assertEqual(self.check(self.project(),
                                    take.replace("'placeholder-launchpad-queue'",
                                                 "'another-queue_2'")), [])
        for value in ("'q ueue'", "'${HOME}'", "'q;id'", "''"):
            with self.subTest(value=value):
                refused = self.check(self.project(),
                                     take.replace("'placeholder-launchpad-queue'", value))
                self.assertEqual(len(refused), 1, refused)
                self.assertIn('R-098/§9.6: R-075 Groovy literal must match', refused[0])

    # -- one line more, or one fixed token changed, is refused -------------------------------

    def test_04_one_extra_line_is_refused(self):
        take = FIXTURE.read_text(encoding='utf-8')
        self.assertEqual(self.check(self.project(), take), [])        # the control passes
        inside = take.replace('    executor = "awsbatch"\n',
                              '    executor = "awsbatch"\n    beforeScript = \'true\'\n')
        extras = {
            'beforeScript inside process': inside,
            'beforeScript appended': take + "\nprocess.beforeScript = 'true'\n",
            'a params block': take + '\nparams {\n    outdir = \'x\'\n}\n',
            'aws.region twice': take + "\naws.region = 'us-east-1'\n",
            'a second process block': take + '\nprocess {\n}\n',
            'a second job tag key': take + "\nprocess.resourceLabels = [project: 'p']\n",
            'the apptainer line': take + "\napptainer.pullTimeout = '90m'\n",
            'an includeConfig': take + "\nincludeConfig 'other.config'\n",
        }
        for label, text in extras.items():
            with self.subTest(extra=label):
                refused = self.check(self.project(), text)
                self.assertEqual(len(refused), 1, refused)
                if label == 'a params block':
                    self.assertIn('contains a params block', refused[0])
                else:
                    self.assertEqual(refused, [REFUSED])

    def test_05_fixed_tokens_are_not_site_values(self):
        """Only queue, region, cliPath and the goal value vary; everything else is grammar."""
        take = FIXTURE.read_text(encoding='utf-8')
        self.assertEqual(self.check(self.project(), take), [])
        swaps = {
            'executor as a site value': ('executor = "awsbatch"', "executor = 'local'"),
            'retry on every failure': ('? "retry" : "finish"', '? "retry" : "retry"'),
            'failures ignored': ('? "retry" : "finish"', '? "retry" : "ignore"'),
            'the outcomes as literals': ('? "retry" : "finish"', "? 'retry' : 'finish'"),
            'no null arm': ('(task.exitStatus == null || task.exitStatus in ((130..145) + 104))',
                            'task.exitStatus in ((130..145) + 104)'),
            'a bigger clamp': ('cpus: 4,', 'cpus: 64,'),
            'more retries': ('maxRetries    = 3', 'maxRetries    = 30'),
            'no job tag': ("    resourceLabels = [goal: 'gars-launch-pad']\n", ''),
            'the 3 Sep two-key tag': ("[goal: 'gars-launch-pad']",
                                      "[goal: 'gars-launch-pad', project: 'epigenome-a']"),
            'another tag key': ("[goal: 'gars-launch-pad']", "[team: 'gars-launch-pad']"),
            'another trace file': ('"pipeline_info/gars_trace.txt"',
                                   '"pipeline_info/other_trace.txt"'),
            'the trace path as a literal': ('"pipeline_info/gars_trace.txt"',
                                            "'pipeline_info/gars_trace.txt'"),
            'fewer trace fields': ('task_id,hash,process', 'task_id,process'),
            'no trace block': ('\ntrace {', '\ntrace_disabled {'),
        }
        for label, (old, new) in swaps.items():
            with self.subTest(swap=label):
                self.assertIn(old, take)
                self.assertEqual(self.check(self.project(), take.replace(old, new, 1)), [REFUSED])

    # -- a name selects a template only as a bare template name ------------------------------

    def test_06_a_name_with_no_protected_template_is_refused(self):
        """A missing template refuses even when the config has the slurm shape (which the old
        check admitted under any name); a template of another kind never selects."""
        slurm = SLURM.read_text(encoding='utf-8')
        cases = {
            'nextflow.pbs.config': slurm,                      # no such template
            'Nextflow.slurm.config': slurm,                    # case-folded on macOS
            'nextflow.slurm.config.bak': slurm,
            'atacseq_bulk.yaml': (TEMPLATES / 'atacseq_bulk.yaml').read_text(encoding='utf-8'),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                project = self.project('name: slurm\nnextflow_config: %s\n' % name)
                refused = self.check(project, text)
                self.assertEqual(len(refused), 1, refused)
                self.assertIn(NO_TEMPLATE, refused[0])
                self.assertTrue(refused[0].startswith('R-098/§9.6: '), refused)

    def test_07_a_path_name_is_refused_and_never_splits_checked_from_passed(self):
        """At 37a8d94 a `sub/` or `../` name made preflight read one file while the wrapper
        passed another with -c: an evil config went through behind a clean decoy. Every path
        form is now refused by the descriptor's own validation, and preflight refuses the
        three that reach it; an absolute name into another project's _config/ is refused
        when the requesting project's descriptor is loaded (prepare)."""
        clean = SLURM.read_text(encoding='utf-8')
        evil = clean + EVIL_LINE

        def decoy_sub(project):
            return project / '_config' / 'sub' / 'sub' / 'nextflow.slurm.config'

        def decoy_up(project):
            return project.parent / 'nextflow.slurm.config'

        cases = [
            ('subdirectory', lambda root, project: 'sub/nextflow.slurm.config', decoy_sub),
            ('dot-dot', lambda root, project: '../nextflow.slurm.config', decoy_up),
            ('absolute', lambda root, project: str(root / 'elsewhere' / 'nextflow.slurm.config'),
             None),
            ('absolute into another project',
             lambda root, project: str(root / 'other' / '_config' / 'nextflow.slurm.config'),
             None),
        ]
        for label, name_for, decoy in cases:
            for text in (evil, clean):
                with self.subTest(name=label, config='evil' if text is evil else 'clean'):
                    root = self.tmp / ('case%d' % self.count)
                    project = self.project(None, root=root)
                    (root / 'other' / '_config').mkdir(parents=True, exist_ok=True)
                    (root / 'other' / '_config' / 'executor.yaml').write_text('name: slurm\n')
                    name = name_for(root, project)
                    descriptor = 'name: slurm\nnextflow_config: %s\n' % name
                    (project / '_config' / 'executor.yaml').write_text(descriptor)
                    self.assertIn(BARE, wl.ex.validate(wl.ex.load(project)))
                    if decoy:
                        target = decoy(project)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(clean)
                    refused = self.check(project, text)
                    if label == 'absolute into another project' and text is clean:
                        # Preflight reads the other project's own descriptor there, so the
                        # requesting project's name is refused where its descriptor is loaded.
                        self.assertEqual(refused, [])
                        sub = project / '02_bioinformatics' / 'atacseq_bulk' / '01_w'
                        sub.mkdir(parents=True)
                        cfg = {'compute.partition': 'p', 'compute.time': '1:00:00',
                               'compute.cpus': '1', 'compute.mem': '1G'}
                        with self.assertRaisesRegex(ValueError, BARE):
                            wl.write_submit_sh(sub, project, cfg, 'proj', 'atacseq_bulk', 'true')
                        self.assertFalse((sub / 'submit.sh').exists())
                    else:
                        self.assertTrue(refused, 'admitted: %s with a %s config' % (label, (
                            'evil' if text is evil else 'clean')))

    def test_08_a_symlinked_template_or_template_folder_is_refused(self):
        """A template the agent could point at its own file must never select: a symlink in
        the template folder, or the folder itself reached through a symlink."""
        real = self.tmp / 'templates'
        real.mkdir()
        for template in (SLURM, AWSBATCH):
            shutil.copyfile(str(template), str(real / template.name))
        evil = SLURM.read_text(encoding='utf-8') + EVIL_LINE
        agent_file = self.tmp / 'agent-written.config'
        agent_file.write_text(evil)
        (real / 'nextflow.linked.config').symlink_to(agent_file)
        (real / 'nextflow.copied.config').write_text(evil)
        linked_dir = self.tmp / 'templates-link'
        linked_dir.symlink_to(real, target_is_directory=True)
        with patch.object(wl, 'EXECUTOR_TEMPLATES', real):
            # the control: a REGULAR file of the same bytes selects, so it is the link that refuses
            project = self.project('name: local\nnextflow_config: nextflow.copied.config\n')
            self.assertEqual(self.check(project, evil), [])
            project = self.project('name: local\nnextflow_config: nextflow.linked.config\n')
            refused = self.check(project, evil)
            self.assertEqual(len(refused), 1, refused)
            self.assertIn(NO_TEMPLATE, refused[0])
            self.assertEqual(self.check(self.project(), AWSBATCH.read_text()), [])
        with patch.object(wl, 'EXECUTOR_TEMPLATES', linked_dir):
            refused = self.check(self.project(), AWSBATCH.read_text())
            self.assertEqual(len(refused), 1, refused)
            self.assertIn(NO_TEMPLATE, refused[0])

    # -- what must not move --------------------------------------------------------------------

    def test_09_slurm_is_unchanged_and_each_grammar_only_under_its_own_name(self):
        slurm = SLURM.read_text(encoding='utf-8')
        for descriptor in (None, 'name: slurm\n'):
            with self.subTest(descriptor=descriptor):
                self.assertEqual(self.check(self.project(descriptor), slurm), [])
                self.assertEqual(self.check(self.project(descriptor), slurm + EVIL_LINE),
                                 [REFUSED])
                self.assertEqual(self.check(self.project(descriptor),
                                            AWSBATCH.read_text(encoding='utf-8')), [REFUSED])
        # and the slurm grammar under the awsbatch name
        self.assertEqual(self.check(self.project(), slurm), [REFUSED])
        # the direct call keeps its contract: no template named means the slurm one
        path = self.tmp / 'executor.config'
        for text, verdict in ((slurm, []), (AWSBATCH.read_text(encoding='utf-8'), [REFUSED])):
            path.write_text(text)
            fails = []
            wl.check_groovy(path, fails)
            self.assertEqual(details(fails), verdict)

    def test_10_the_manifest_records_the_bytes_passed_with_c(self):
        """R9's execution evidence is still the sha256 of the file the submit body passes."""
        project = self.project()
        passed = wl.ex.nextflow_config_path(project)
        passed.write_bytes(FIXTURE.read_bytes())
        fails = []
        wl.check_executor_config(passed, fails)
        self.assertEqual(fails, [])
        sub = project / '02_bioinformatics' / 'atacseq_bulk' / '01_nfcore-atacseq-wrapper'
        sub.mkdir(parents=True)
        # The -c line exactly as the nf-core wrappers render it (test_07d2 pins that they do).
        body = 'nextflow run "x" \\\n    -c "%s" \\\n    -params-file "%s/params.yaml" \\\n    $RESUME' % (
            wl.shell_value(passed.resolve(), 'executor_config'), sub.resolve())
        cfg = {'compute.partition': 'p', 'compute.time': '1:00:00', 'compute.cpus': '1',
               'compute.mem': '1G'}
        wl.write_submit_sh(sub, project, cfg, 'proj', 'atacseq_bulk', body)
        wl.write_reproducibility(sub, 'atacseq_bulk', sub, {}, [])
        import json
        manifest = json.loads((sub / 'reproducibility' / 'manifest.json').read_text())
        entries = {e['role']: e for e in manifest['execution_config']}
        self.assertEqual(sorted(entries), ['executor_descriptor', 'nextflow_config'])
        recorded = entries['nextflow_config']
        self.assertEqual(recorded['sha256'], hashlib.sha256(FIXTURE.read_bytes()).hexdigest())
        self.assertEqual(recorded['path'],
                         os.path.relpath(str(passed.resolve()), str(REPO)))
        self.assertEqual(entries['executor_descriptor']['sha256'],
                         hashlib.sha256(RIG.encode('utf-8')).hexdigest())
        self.assertEqual(manifest['execution_config_resolved'],
                         {'backend': 'local', 'nextflow_config': 'nextflow.awsbatch.config',
                          'nextflow_profile': ''})
        script = (sub / 'submit.sh').read_text()
        tokens = shlex.split(script.split('nextflow run', 1)[1].replace('\\\n', ' '))
        self.assertEqual(Path(tokens[tokens.index('-c') + 1]), passed.resolve())

    def test_11_the_template_carries_what_the_ruling_names(self):
        """The template's own content: four site values, one job-tag key, the trace the
        manifest reads, and nothing the slurm cluster needed and Batch does not."""
        import re
        text = re.sub(r'//[^\n]*', '', AWSBATCH.read_text(encoding='utf-8'))
        sites = re.findall(r"(\w+)\s*(?:=|:)\s*'[^']*'", text)
        self.assertEqual(sites, ['queue', 'goal', 'region', 'cliPath'])
        self.assertEqual(re.findall(r'resourceLabels\s*=\s*\[([^\]]*)\]', text),
                         [" goal: 'untagged' "])
        self.assertIn('executor = "awsbatch"', text)
        self.assertIn('? "retry" : "finish"', text)
        self.assertIn('task.exitStatus == null', text)
        trace_file = re.search(r'file\s*=\s*"([^"]+)"', text).group(1)
        self.assertIn("'run/%s'" % trace_file,
                      (GARS / '_system' / 'wrapperlib.py').read_text(encoding='utf-8'))
        slurm_fields = re.search(r'fields = ("[^"]+")', SLURM.read_text(encoding='utf-8')).group(1)
        self.assertIn('fields    = %s' % slurm_fields, text)
        for absent in ('params', 'apptainer', 'beforeScript', 'includeConfig', '$', 'workDir'):
            self.assertNotIn(absent, text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
