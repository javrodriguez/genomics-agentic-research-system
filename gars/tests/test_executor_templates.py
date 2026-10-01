"""0251: one protected executor template per descriptor `nextflow_config` name.

`check_groovy` compared every executor config with `nextflow.slurm.config`, whatever the
descriptor named, so an AWS Batch venue could not pass preflight (the launch pad's refusal at
37a8d94). It now compares with `_templates/config/<the descriptor's nextflow_config name>`.
That WIDENS a guard, so most of this module is about what must still be refused: any other
grammar, any name that is not a bare template name, a symlinked template, and a config the
check reads that is not the one the wrapper passes with -c.
Since glitch-14's ruling of 30 Sep 2026 (exact render equality), a Batch config is admitted only
as the template's bytes with its three slots filled by values their validators admit; the slurm
config keeps the shape check. FIXTURE is such a rendering, the shape the demo's generator writes.
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
# The FIXTURE's slot values: placeholders, never a real queue or region.
SLOTS = {'queue': 'placeholder-launchpad-queue', 'goal': 'gars-launch-pad', 'region': 'zz-test-1'}
EVIL_LINE = '\nprocess.beforeScript = "touch _system/x"\n'


def details(fails):
    return [f['detail'] for f in fails]


def double_quoted_spans(text):
    """(start, end) of each double-quoted string on a code line (a `//` line is a comment)."""
    spans, offset = [], 0
    for line in text.splitlines(keepends=True):
        if not line.lstrip().startswith('//'):
            start = line.find('"')
            while start >= 0:
                end = line.index('"', start + 1) + 1
                spans.append((offset + start, offset + end))
                start = line.find('"', end)
        offset += len(line)
    return spans


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

    def test_01_a_rendering_is_admitted_and_the_raw_template_is_not(self):
        """Failed while check_groovy compared every config with the slurm template; since the
        render ruling, the template's own bytes (its slots unfilled) are not a rendering."""
        self.assertEqual(self.check(self.project(), FIXTURE.read_text(encoding='utf-8')), [])
        refused = self.check(self.project(), AWSBATCH.read_text(encoding='utf-8'))
        self.assertEqual(len(refused), 1, refused)
        self.assertIn('slot must match', refused[0])      # names the alphabetically first unfilled slot

    def test_02_the_generator_shape_is_admitted_for_a_take_and_a_rehearsal(self):
        """The D generator's output (a rendering) passes, and a rehearsal differs from the take
        only in the one job-tag value."""
        take = FIXTURE.read_text(encoding='utf-8')
        rehearsal = take.replace("goal: 'gars-launch-pad'", "goal: 'gars-launch-pad-rehearsal'")
        changed = [(a, b) for a, b in zip(take.splitlines(), rehearsal.splitlines()) if a != b]
        self.assertEqual(len(changed), 1, changed)
        for text in (take, rehearsal):
            self.assertEqual(self.check(self.project(), text), [])

    def test_03_a_new_site_value_passes_and_an_unsafe_one_is_refused(self):
        """A slot holds a value its validator admits, nothing more."""
        take = FIXTURE.read_text(encoding='utf-8')
        self.assertEqual(self.check(self.project(),
                                    take.replace("'placeholder-launchpad-queue'",
                                                 "'another-queue_2'")), [])
        for value in ("'q ueue'", "'${HOME}'", "'q;id'", "''"):
            with self.subTest(value=value):
                refused = self.check(self.project(),
                                     take.replace("'placeholder-launchpad-queue'", value))
                self.assertEqual(len(refused), 1, refused)
                self.assertTrue(refused[0].startswith('R-098/§9.6: '), refused)
                self.assertIn('queue', refused[0])
        # Under the slurm name a single-quoted literal is still held to R-075's charset.
        slurm = SLURM.read_text(encoding='utf-8')
        self.assertEqual(slurm.count("'cpu_long'"), 1)
        refused = self.check(self.project('name: slurm\n'), slurm.replace("'cpu_long'", "'cpu;long'"))
        self.assertEqual(len(refused), 1, refused)
        self.assertIn('R-075 Groovy literal must match', refused[0])

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
        """Only the queue, the region and the goal value vary; everything else is fixed."""
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
            'no job tag': ("    resourceLabels = [ goal: 'gars-launch-pad' ]\n", ''),
            'the 3 Sep two-key tag': ("[ goal: 'gars-launch-pad' ]",
                                      "[ goal: 'gars-launch-pad', project: 'epigenome-a' ]"),
            'another tag key': ("[ goal: 'gars-launch-pad' ]", "[ team: 'gars-launch-pad' ]"),
            'the cliPath as a slot': ("cliPath = '/opt/nf-tools/bin/aws'", "cliPath = '/usr/local/bin/aws'"),
            'another trace file': ('"pipeline_info/gars_trace.txt"',
                                   '"pipeline_info/other_trace.txt"'),
            'the trace path as a literal': ('"pipeline_info/gars_trace.txt"',
                                            "'pipeline_info/gars_trace.txt'"),
            'fewer trace fields': ('"task_id,hash,', '"task_id,'),
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
        # `.` and `..` name no file in _config/ either (0251 item 3).
        for name in ('.', '..'):
            with self.subTest(name=name):
                project = self.project('name: slurm\nnextflow_config: %s\n' % name)
                self.assertIn(BARE, wl.ex.validate(wl.ex.load(project)))

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
            self.assertEqual(self.check(self.project(), FIXTURE.read_text()), [])
            # A link that stays inside the folder is still a link; a regular file whose name only
            # starts like a template name, or carries upper case, names no template.
            (real / 'nextflow.inner.config').symlink_to(real / 'nextflow.copied.config')
            (real / 'nextflow.copied.config.bak').write_text(evil)
            (real / 'nextflow.Upper.config').write_text(evil)
            for name in ('nextflow.inner.config', 'nextflow.copied.config.bak',
                         'nextflow.Upper.config'):
                with self.subTest(name=name):
                    project = self.project('name: local\nnextflow_config: %s\n' % name)
                    refused = self.check(project, evil)
                    self.assertEqual(len(refused), 1, refused)
                    self.assertIn(NO_TEMPLATE, refused[0])
        with patch.object(wl, 'EXECUTOR_TEMPLATES', linked_dir):
            refused = self.check(self.project(), FIXTURE.read_text())
            self.assertEqual(len(refused), 1, refused)
            self.assertIn(NO_TEMPLATE, refused[0])
        # A rendered template that does not declare each of its slots once is refused, never
        # compiled (a slot twice would be a regular-expression error, not a refusal).
        malformed = self.tmp / 'malformed'
        malformed.mkdir()
        shutil.copyfile(str(SLURM), str(malformed / SLURM.name))
        (malformed / AWSBATCH.name).write_text(
            AWSBATCH.read_text(encoding='utf-8').replace('{{region}}', '{{queue}}'), encoding='utf-8')
        with patch.object(wl, 'EXECUTOR_TEMPLATES', malformed):
            refused = self.check(self.project(), FIXTURE.read_text())
            self.assertEqual(len(refused), 1, refused)
            self.assertIn('does not declare each of its slots once', refused[0])

    # -- what must not move --------------------------------------------------------------------

    def test_09_slurm_is_unchanged_and_each_grammar_only_under_its_own_name(self):
        slurm = SLURM.read_text(encoding='utf-8')
        for descriptor in (None, 'name: slurm\n'):
            with self.subTest(descriptor=descriptor):
                self.assertEqual(self.check(self.project(descriptor), slurm), [])
                self.assertEqual(self.check(self.project(descriptor), slurm + EVIL_LINE),
                                 [REFUSED])
                self.assertEqual(self.check(self.project(descriptor),
                                            FIXTURE.read_text(encoding='utf-8')), [REFUSED])
        # and the slurm grammar under the awsbatch name
        self.assertEqual(self.check(self.project(), slurm), [REFUSED])
        # the direct call keeps its contract: no template named means the slurm one
        path = self.tmp / 'executor.config'
        for text, verdict in ((slurm, []), (FIXTURE.read_text(encoding='utf-8'), [REFUSED])):
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
        # The render ruling: the manifest also records the slot values and the rendering's hash.
        self.assertEqual(manifest['execution_config_rendered'], {
            'template': 'nextflow.awsbatch.config',
            'template_sha256': hashlib.sha256(AWSBATCH.read_bytes()).hexdigest(),
            'slots': SLOTS,
            'rendered_sha256': hashlib.sha256(FIXTURE.read_bytes()).hexdigest()})

    def test_11_the_template_carries_what_the_ruling_names(self):
        """The template's own content: exactly three slots (queue, goal, region), each once and
        inside single quotes; one job-tag key; the fixed cliPath; the trace the manifest reads;
        and nothing the slurm cluster needed and Batch does not."""
        import re
        raw = AWSBATCH.read_text(encoding='utf-8')
        self.assertEqual(re.findall(r"\{\{([a-z]+)\}\}", raw), ['queue', 'goal', 'region'])
        self.assertEqual((raw.count('{{'), raw.count('}}')), (3, 3))
        for slot in ('queue', 'goal', 'region'):
            self.assertIn("'{{%s}}'" % slot, raw)
        self.assertEqual(sorted(wl.EXECUTOR_RENDER_SLOTS['nextflow.awsbatch.config']),
                         ['goal', 'queue', 'region'])
        text = re.sub(r'//[^\n]*', '', raw)
        self.assertEqual(re.findall(r'resourceLabels\s*=\s*\[([^\]]*)\]', text),
                         [" goal: '{{goal}}' "])
        self.assertIn("cliPath = '/opt/nf-tools/bin/aws'", text)
        self.assertIn('executor = "awsbatch"', text)
        self.assertIn('? "retry" : "finish"', text)
        self.assertIn('task.exitStatus == null', text)
        trace_file = re.search(r'file\s*=\s*"([^"]+)"', text).group(1)
        self.assertIn("'run/%s'" % trace_file,
                      (GARS / '_system' / 'wrapperlib.py').read_text(encoding='utf-8'))
        for absent in ('params', 'apptainer', 'beforeScript', 'includeConfig', '$', 'workDir'):
            self.assertNotIn(absent, text)

    # -- review r1 ------------------------------------------------------------------------------

    def test_12_a_double_quoted_string_is_compared_byte_for_byte(self):
        """L5-R1-1 and L5-R1-2: the shape stripped `//` comments before it read any string, so
        string text after a `//` left the shape, and whitespace inside a string was dropped.
        For every double-quoted string of both templates: a `//` and one extra statement inside
        it (the string closed on the next line), and one added space inside it, are refused."""
        extra = '// process.maxRetries = 3\n'
        for template, descriptor, count in ((SLURM, 'name: slurm\n', 1), (FIXTURE, RIG, 6)):
            text = template.read_text(encoding='utf-8')
            spans = double_quoted_spans(text)
            self.assertEqual(len(spans), count, [text[a:b] for a, b in spans])
            self.assertEqual(self.check(self.project(descriptor), text), [])    # the control
            for start, end in spans:
                for label, inside in (('a // and an extra statement', extra), ('a space', ' ')):
                    with self.subTest(template=template.name, string=text[start:end], case=label):
                        changed = text[:end - 1] + inside + text[end - 1:]
                        self.assertEqual(self.check(self.project(descriptor), changed), [REFUSED])

    def test_13_a_nested_config_folder_never_changes_the_project_checked(self):
        """L5-R1-3: preflight found its project by walking up from the config's folder, so a
        `_config/_config/executor.yaml` made it read that descriptor (`name: local`, no config
        demanded) and return early, while the wrapper still passes the project's own
        `_config/nextflow.awsbatch.config` with -c."""
        project = self.project()
        nested = project / '_config' / '_config'
        nested.mkdir()
        (nested / 'executor.yaml').write_text('name: local\n', encoding='utf-8')
        template = FIXTURE.read_text(encoding='utf-8')
        self.assertEqual(self.check(project, template + '\nprocess.maxRetries = 3\n'), [REFUSED])
        self.assertEqual(self.check(project, template), [])
        # and when the nested descriptor names another config, its clean sibling is not what
        # gets checked in place of the file passed
        project = self.project()
        nested = project / '_config' / '_config'
        nested.mkdir()
        (nested / 'executor.yaml').write_text('name: slurm\n', encoding='utf-8')
        (project / '_config' / 'nextflow.slurm.config').write_text(
            SLURM.read_text(encoding='utf-8'), encoding='utf-8')
        self.assertEqual(self.check(project, template + '\nprocess.maxRetries = 3\n'), [REFUSED])

    def test_14_the_trace_carries_what_the_launch_pad_reads(self):
        """F-L3-3: a -c config's trace scope replaces nf-core's own, so these fields are the only
        trace a Batch run writes. The launch pad's `jobs` finds the Batch job ids in `native_id`
        (with `task_id` and `name`), and its smoke verdict reads `exit`; the slurm template's
        fields stay, in order. collect's `trace_evidence` reads columns by header name, so it
        still reads a trace carrying the two added ones."""
        import re
        def fields(path):
            return re.search(r'fields\s*=\s*"([^"]+)"', path.read_text(encoding='utf-8')).group(1).split(',')
        batch = fields(AWSBATCH)
        self.assertEqual(batch, ['task_id', 'hash', 'native_id', 'process', 'name', 'status', 'exit',
                                 'container', 'start', 'complete', 'realtime', '%cpu', 'rss',
                                 'cpus'])
        self.assertEqual([f for f in batch if f not in ('native_id', 'exit')], fields(SLURM))
        self.assertEqual(fields(FIXTURE), batch)
        stage = self.tmp / 'stage'
        (stage / 'run' / 'pipeline_info').mkdir(parents=True)
        image = 'quay.io/biocontainers/x@sha256:' + 'a' * 64
        row = {'task_id': '1', 'hash': 'ab/cdef12', 'native_id': '0f8fad5b-d9cb-469f-a165-70867728950e',
               'process': 'NFCORE:FASTQC', 'name': 'FASTQC (1)', 'status': 'COMPLETED', 'exit': '0',
               'container': image, 'start': '2026-10-05 08:00:00.000',
               'complete': '2026-10-05 08:05:00.000', 'realtime': '5m', '%cpu': '99.0%',
               'rss': '1 GB', 'cpus': '1'}
        (stage / 'run' / 'pipeline_info' / 'gars_trace.txt').write_text(
            '\t'.join(batch) + '\n' + '\t'.join(row[f] for f in batch) + '\n', encoding='utf-8')
        containers, execution = wl.trace_evidence(stage)
        self.assertEqual(containers, [{'process': 'NFCORE:FASTQC', 'image': image,
                                       'digest': 'sha256:' + 'a' * 64}])
        self.assertEqual(execution, {'start': '2026-10-05 08:00:00.000',
                                     'complete': '2026-10-05 08:05:00.000'})

    # -- review r2 ------------------------------------------------------------------------------

    def test_15_word_and_line_boundaries_are_compared(self):
        """L5-R2-1: outside strings the shape made every character its own token and dropped
        every newline and comment, so an identifier split in two, or two statements joined on one
        line, had the template's shape. Groovy reads an identifier or a number as one token and a
        newline or a `//` comment as a line end; so does the shape now. Only space, tab, CR and LF
        are whitespace; CR and U+FFFF end a comment as in Groovy. Each case is refused under both
        names, the table run on a Batch rendering and again on the slurm template, so the slurm
        lexer stays pinned (review r3, R3-1). Comments and blank lines stay free for slurm's shape
        check (the control) and not for a Batch rendering, whose every byte is fixed."""
        text = FIXTURE.read_text(encoding='utf-8')
        self.assertEqual(self.check(self.project(), text), [])
        free = text.replace('    maxRetries    = 3\n', '    maxRetries = 3   // a comment\n\n\n')
        self.assertEqual(self.check(self.project(), free), [REFUSED])
        slurm_free = SLURM.read_text(encoding='utf-8').replace(
            '    maxRetries    = 3\n', '    maxRetries = 3   // a comment\n\n\n')
        self.assertEqual(self.check(self.project('name: slurm\n'), slurm_free), [])
        cases = {
            'an identifier split by a space': ('maxRetries    = 3', 'max Retries    = 3'),
            'an identifier split by a newline': ('resourceLabels = [', 'resource\nLabels = ['),
            'an identifier split by a comment': ('maxRetries    = 3', 'max// c\nRetries    = 3'),
            'a number split by a space': ('queueSize       = 20', 'queueSize       = 2 0'),
            'two statements joined on one line': ('"finish" }\n    maxRetries', '"finish" }    maxRetries'),
            'a no-break space inside an identifier': ('maxRetries    = 3', 'max\u00a0Retries    = 3'),
            'CR ends a comment': ('// Both outcomes are fixed, never slots.\n',
                                  '// Both outcomes are fixed, never slots.\rprocess.maxRetries = 3\n'),
            'U+FFFF ends a comment': ('// Both outcomes are fixed, never slots.\n',
                                      '// Both outcomes are fixed, never slots.\uffffprocess.maxRetries = 3\n'),
        }
        for label, (old, new) in cases.items():
            with self.subTest(case=label):
                self.assertEqual(text.count(old), 1, label)
                self.assertEqual(self.check(self.project(), text.replace(old, new)), [REFUSED])
        slurm = SLURM.read_text(encoding='utf-8')
        comment = '    // 130..145 covers the SIGTERM/SIGKILL family; 104 is a common transient.\n'
        slurm_cases = {
            'an identifier split by a space': ('maxRetries    = 3', 'max Retries    = 3'),
            'an identifier split by a newline': ('errorStrategy = {', 'error\nStrategy = {'),
            'an identifier split by a comment': ('maxRetries    = 3', 'max// c\nRetries    = 3'),
            'a number split by a space': ('queueSize       = 20', 'queueSize       = 2 0'),
            'a name split by a space': ('queueSize       = 20', 'queue Size       = 20'),
            'two statements joined on one line': ("'finish' }\n    maxRetries", "'finish' }    maxRetries"),
            'a no-break space inside an identifier': ('maxRetries    = 3', 'max\u00a0Retries    = 3'),
            'a no-break space between two tokens': ('maxRetries    = 3', 'maxRetries\u00a0   = 3'),
            'CR ends a comment': (comment, comment[:-1] + '\rprocess.maxRetries = 3\n'),
            'U+FFFF ends a comment': (comment, comment[:-1] + '\uffffprocess.maxRetries = 3\n'),
            'an operator split by a space': ('(130..145)', '(130. .145)'),
        }
        for label, (old, new) in slurm_cases.items():
            with self.subTest(template='slurm', case=label):
                self.assertEqual(slurm.count(old), 1, label)
                self.assertEqual(self.check(self.project('name: slurm\n'), slurm.replace(old, new)),
                                 [REFUSED])
        # A quote left open at the end of the file is refused, never read as the end of the text.
        refused = self.check(self.project('name: slurm\n'), slurm + "'process.maxRetries = 3\n")
        self.assertEqual(len(refused), 1, refused)
        self.assertIn('unterminated string', refused[0])

    def test_16_a_descriptor_naming_no_config_still_has_the_passed_file_checked(self):
        """L5-R2-2: with no config named (`name: local`, or `name: slurm` blanked), preflight
        returned early while the wrappers pass their fallback `_config/nextflow.slurm.config`
        with -c. The file passed is now checked against the slurm template; an explicitly blank
        name on a backend that pairs with a config is refused by the descriptor's validation."""
        slurm = SLURM.read_text(encoding='utf-8')
        extra = slurm + '\nprocess.maxRetries = 3\n'
        blank = '_config/executor.yaml: R-075: nextflow_config may not be blank for this backend'
        missing = 'no _config/nextflow.slurm.config -- stage 00 seeds it'
        for descriptor, problems in (('name: local\n', []),
                                     ("name: slurm\nnextflow_config: ''\n", [blank])):
            with self.subTest(descriptor=descriptor):
                # none present: the wrapper would still pass it with -c (review r3, R3-2)
                self.assertEqual(self.check(self.project(descriptor)), problems + [missing])
                self.assertEqual(self.check(self.project(descriptor), slurm), problems)
                self.assertEqual(self.check(self.project(descriptor), extra), problems + [REFUSED])


    # -- glitch-14's render ruling (30 Sep 2026) ------------------------------------------------

    def test_17_only_an_exact_rendering_is_admitted(self):
        """A Batch config is the template's bytes with each slot replaced by a value its validator
        admits: no quote, backslash, newline, `$`, brace or space, not empty, not over-long.
        Comments, spacing, line ends and the final newline are the template's; an expression in a
        value's place, or any other byte, is refused."""
        take = FIXTURE.read_text(encoding='utf-8')
        self.assertEqual(self.check(self.project(), take), [])
        injected = ["x'y", 'x\ny', '${HOME}', 'x\\y', 'x y', 'x{1}', 'x$y', 'x"y', '', 'a' * 129]
        for slot, value in SLOTS.items():
            self.assertEqual(take.count("'%s'" % value), 1, slot)
            for bad in injected + (['US-EAST-1', 'us-east-1a'] if slot == 'region' else []):
                with self.subTest(slot=slot, value=bad):
                    refused = self.check(self.project(), take.replace("'%s'" % value, "'%s'" % bad))
                    self.assertEqual(len(refused), 1, refused)
                    self.assertTrue(refused[0].startswith('R-098/§9.6: '), refused)
        others = {
            'a comment reworded': take.replace('never slots.', 'never slot values.'),
            'spacing changed': take.replace('maxRetries    = 3', 'maxRetries = 3'),
            'a trailing comment added': take.replace('    maxRetries    = 3\n',
                                                     '    maxRetries    = 3 // x\n'),
            'a blank line added': take.replace('process {\n', 'process {\n\n'),
            'the final newline dropped': take.rstrip('\n'),
            'CRLF line ends': take.replace('\n', '\r\n'),
            'an expression as the tag value': take.replace("goal: 'gars-launch-pad'", 'goal: task.name'),
        }
        for label, text in others.items():
            with self.subTest(case=label):
                self.assertNotEqual(text, take)
                self.assertEqual(self.check(self.project(), text), [REFUSED])

    def test_18_a_config_link_is_admitted_only_as_a_replay_binds_it(self):
        """Review r3 (R3-3) and the rulings of 30 Sep 2026 (option A, and glitch-14's containment
        rule): scripts/rerun_check.py binds a replay's `_config/<name>` as a link into the original
        project, so a link is admitted only when its final realpath has the same name and lies
        inside this workspace's projects; its target's bytes are what is checked. Prepare keys the
        rendering check and the render record on the descriptor's name, and refuses (before
        submit.sh is written) a `-c` config of another name or one that is not a rendering."""
        take = FIXTURE.read_text(encoding='utf-8')
        name = AWSBATCH.name
        root = self.tmp / 'projects-root'
        inside = root / 'original' / '_config'
        inside.mkdir(parents=True)
        (inside / name).write_text(take, encoding='utf-8')
        (inside / 'other.config').write_text(take, encoding='utf-8')
        bad = root / 'original-2' / '_config'
        bad.mkdir(parents=True)
        (bad / name).write_text(take + '\nprocess.maxRetries = 3\n', encoding='utf-8')
        outside = self.tmp / 'elsewhere' / '_config'
        outside.mkdir(parents=True)
        (outside / name).write_text(take, encoding='utf-8')
        hop_out = self.tmp / 'hop-outside'
        hop_out.mkdir()
        (hop_out / 'hop.config').symlink_to(inside / name)          # a chain that ends inside
        evil = self.tmp / 'projects-root-evil' / 'original' / '_config'  # shares the root's prefix
        evil.mkdir(parents=True)
        (evil / name).write_text(take, encoding='utf-8')
        (inside / 'hop-back.config').symlink_to(outside / name)      # a chain that ends outside
        OUTSIDE = "resolves outside this workspace's projects"
        OTHER = 'resolves to a different config name'
        cases = [
            ('same name, inside', inside / name, None),
            ('same name, outside', outside / name, OUTSIDE),
            ('another name, inside', inside / 'other.config', OTHER),
            ('same name, inside, not a rendering', bad / name, 'unregistered Groovy grammar'),
            ('a chain ending inside', hop_out / 'hop.config', None),
            ('a chain ending outside', inside / 'hop-back.config', OUTSIDE),
            ('a sibling folder sharing the root as a string prefix', evil / name, OUTSIDE),
            ('a dangling link inside', inside / 'missing' / name, 'stage 00 seeds it'),
        ]
        with patch.object(wl, 'EXECUTOR_PROJECTS', root):
            for label, target, refusal in cases:
                with self.subTest(case=label):
                    project = self.project()
                    wl.ex.nextflow_config_path(project).symlink_to(target)
                    refused = self.check(project)
                    if refusal is None:
                        self.assertEqual(refused, [])
                    else:
                        self.assertEqual(len(refused), 1, refused)
                        self.assertIn(refusal, refused[0])
            cfg = {'compute.partition': 'p', 'compute.time': '1:00:00', 'compute.cpus': '1',
                   'compute.mem': '1G'}

            def prepare(project, passed):
                sub = project / '02_bioinformatics' / 'atacseq_bulk' / '01_nfcore-atacseq-wrapper'
                sub.mkdir(parents=True)
                body = 'nextflow run "x" \\\n    -c "%s" \\\n    -params-file "%s/params.yaml"' % (
                    wl.shell_value(passed.resolve(), 'executor_config'), sub.resolve())
                wl.write_submit_sh(sub, project, cfg, 'proj', 'atacseq_bulk', body)
                return sub

            # a replay-bound link: the record is written, keyed on the descriptor's name
            project = self.project()
            passed = wl.ex.nextflow_config_path(project)
            passed.symlink_to(inside / name)
            sub = prepare(project, passed)
            wl.write_reproducibility(sub, 'atacseq_bulk', sub, {}, [])
            import json
            manifest = json.loads((sub / 'reproducibility' / 'manifest.json').read_text())
            self.assertEqual(manifest['execution_config_rendered']['template'], name)
            self.assertEqual(manifest['execution_config_rendered']['slots'], SLOTS)
            # -c of another name under a rendered descriptor name, or a non-rendering: refused
            for label, target, message in (
                    ('another name', inside / 'other.config', "is not the descriptor's"),
                    ('not a rendering', bad / name, 'is not a rendering of its template')):
                with self.subTest(prepare=label):
                    project = self.project()
                    sub = project / '02_bioinformatics' / 'atacseq_bulk' / '01_nfcore-atacseq-wrapper'
                    linked = project / '_config' / target.name     # bound as a replay binds it
                    linked.symlink_to(target)
                    with self.assertRaisesRegex(ValueError, message):
                        prepare(project, linked)
                    self.assertFalse((sub / 'submit.sh').exists())

        # Review of the link ruling, L5-L-1: preflight, the record and the submit command use
        # one project. An empty, agent-writable `_config/` folder planted between the project and
        # the substage made prepare read the built-in slurm descriptor while passing the Batch
        # rendering with -c, writing submit.sh with no render record. Each form is refused
        # before submit.sh is written.
        def planted(descriptor, config_name, text):
            project = self.project(descriptor)
            passed = project / '_config' / config_name
            passed.write_text(text, encoding='utf-8')
            sub = project / '02_bioinformatics' / 'atacseq_bulk' / '01_nfcore-atacseq-wrapper'
            (sub.parent / '_config').mkdir(parents=True)
            return project, passed, sub

        slurm = SLURM.read_text(encoding='utf-8')
        forms = [
            ("the review's probe: the Batch rendering behind a planted _config/",
             planted(RIG, name, take), "is not the descriptor's|of the project prepare reads"),
            ('a slurm config behind a planted _config/',
             planted('name: slurm\n', SLURM.name, slurm), 'of the project prepare reads'),
        ]
        project = self.project('name: slurm\n')                  # no planted folder
        passed = project / '_config' / name
        passed.write_text(take, encoding='utf-8')
        forms.append(('a rendered -c name under a descriptor that names slurm',
                      (project, passed, project / '02_bioinformatics' / 'atacseq_bulk' / '01_w'),
                      "is not the descriptor's"))
        # The review of the fix (L5-F-1): one config file is not yet one descriptor. A planted
        # folder holding its own executor.yaml (and the project's config, or a link to it) must
        # not become the project prepare reads, whichever way the -c file is reached.
        other = "name: slurm\nnextflow_config: nextflow.awsbatch.config\n"
        DEPTH = "is not the substage's project"

        def planted_descriptor(where):
            project = self.project()
            real = project / '_config' / name
            sub = project / '02_bioinformatics' / 'atacseq_bulk' / '01_nfcore-atacseq-wrapper'
            folder = (sub.parent if where == 'assay' else sub) / '_config'
            folder.mkdir(parents=True)
            (folder / 'executor.yaml').write_text(other, encoding='utf-8')
            return project, real, sub, folder

        project, real, sub, folder = planted_descriptor('assay')         # T1c+
        real.write_text(take, encoding='utf-8')
        (folder / name).symlink_to(real)
        forms.append(('T1c+: a planted _config/ linking to the project config', (project, real, sub), DEPTH))
        for where, label in (('assay', 'T2a'), ('substage', 'T2b')):
            project, real, sub, folder = planted_descriptor(where)
            (folder / name).write_text(take, encoding='utf-8')
            real.symlink_to(folder / name)
            forms.append(('%s: the project link into a planted %s _config/' % (label, where),
                          (project, real, sub), DEPTH))
        for label, (project, passed, sub), message in forms:
            with self.subTest(prepare=label):
                sub.mkdir(parents=True, exist_ok=True)
                with self.assertRaisesRegex(ValueError, message):
                    wl.write_submit_sh(sub, project, cfg, 'proj', 'atacseq_bulk',
                                       'nextflow run "x" \\\n    -c "%s" \\\n    -params-file "%s/params.yaml"' % (
                                           wl.shell_value(passed.resolve(), 'executor_config'), sub.resolve()))
                self.assertFalse((sub / 'submit.sh').exists())

if __name__ == '__main__':
    unittest.main(verbosity=2)
