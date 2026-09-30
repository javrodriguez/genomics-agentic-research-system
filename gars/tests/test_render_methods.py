"""The Methods renderer: every line traced to a record field, nothing invented, nothing guessed.

The oracle below is this test's own restatement of the output's closed vocabulary, written from
the specification and independent of the renderer's code: its own JSON and HISTORY readers, its
own code-span, absence and path-like rules, and its own derivation of which lines a set of records
must produce. For every line the renderer lists under Sources, the oracle rebuilds the expected
text from the cited record fields, read here from the input files, and requires byte equality.
"""
import argparse
import ast
import builtins
import collections
import contextlib
import copy
import hashlib
import io
import json
import os
import pwd
import re
import shutil
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path
from unittest import mock
from support import GARS, module, run, write_fixture_dataset

CLAIMS = GARS / '_system/claims'
FIXTURE = GARS / 'tests/fixtures/methods'
# Import must fail naming the absent production path.
renderer = module(CLAIMS / 'render_methods.py', 'methods_renderer')

# ---- the oracle: the output's closed vocabulary, restated ---------------------------------------

T_NOT = 'not recorded'
T_WITHHELD = 'a path-like value, withheld'
T_BY = 'by the approver the run recorded'
T_NOBY = 'with no approver named in its approval record'
# An absolute path starts where no letter, digit or one of . _ ~ / : \ - comes before it (so a/b and
# ./b are relative), or right after a colon when one slash follows (host:/x, not https://x).
PATH_LIKE = re.compile(r'''(?<![A-Za-z0-9._~/:\\-])(?:/|~[^\s/"']*/|\\|[A-Za-z]:[\\/])|(?<=:)/(?!/)'''
                       r'''|(?<![A-Za-z0-9])file:''', re.I)
HEADINGS = ('# Methods', '## Parameters', '## Software used', '## Citation', '## Records read', '## Sources')
PARA, PARAM, SOFT, CITE, READ = HEADINGS[:5]
# kind: (section heading, fixed text, slot types) -- v value, p approver phrase, a absent, x unprinted
KINDS = {
    'workflow': (PARA, 'The run manifest of workflow {} records: version {}; pipeline commit {}; '
                       'GARS wrapper {}; GARS commit {}; template version {}; status {}.', 'vvvvvvv'),
    'failure': (PARA, 'Its failure class is {}.', 'v'),
    'reference': (PARA, 'Its reference genome: build {}; annotation release {}; '
                        'FASTA sha256 {}; GTF sha256 {}.', 'vvvv'),
    'reference-check': (PARA, 'Its reference registry check reads {}, reason {}.', 'vv'),
    'reference-absent': (PARA, 'Its reference genome is not recorded.', 'a'),
    'config': (PARA, 'Its configuration sha256 is {}.', 'v'),
    'threads': (PARA, 'Its thread count is {}.', 'v'),
    'command': (PARA, 'Its exact submission: {}, sha256 {}.', 'vv'),
    'command-absent': (PARA, 'Its exact submission is not recorded.', 'a'),
    'agent': (PARA, 'Its agent model is {}.', 'v'),
    'model-step': (PARA, 'It records a model-mediated step: model {}; provider {}; contract {}; '
                         'git blob {}.', 'vvvv'),
    'model-steps-absent': (PARA, 'Its model-mediated steps are not recorded.', 'a'),
    'pointer': (PARA, "Each workflow's parameters, random seeds, software versions and container "
                      "images are listed below.", ''),
    'approval': (PARA, 'The analysis plan with sha256 {} was approved at {} {}.', 'vvp'),
    'history': (PARA, "The project's history records {} as {} on {}, with model {} and template "
                      "version {}.", 'vvvvv'),
    'history-absent': (PARA, "The approved analysis's completion is not recorded in the project's "
                             "history.", 'xx'),
    'param': (PARAM, '- {} parameter {}: {}.', 'vvv'),
    'params-absent': (PARAM, '- {}: parameters are not recorded.', 'va'),
    'seed': (PARAM, '- {} random seed for {}: {}.', 'vvv'),
    'seed-unset': (PARAM, '- {} random seed for {}: not recorded; seed supported {}, determinism {}.',
                   'vvvva'),
    'seeds-text': (PARAM, '- {} random seeds: {}.', 'vv'),
    'seeds-absent': (PARAM, '- {}: random seeds are not recorded.', 'va'),
    'gars': (SOFT, '- GARS commit {}, template version {} (workflow {}).', 'vvv'),
    'workflow-version': (SOFT, '- Workflow {} version {}, pipeline commit {}.', 'vvv'),
    'versions-file': (SOFT, '- {} software versions (file {}, sha256 {}):', 'vvv'),
    'version': (SOFT, '  - {}: {}.', 'vv'),
    'version-absent': (SOFT, '  - versions not recorded.', 'a'),
    'versions-absent': (SOFT, '- {}: software versions are not recorded.', 'va'),
    'container': (SOFT, '- {} container for process {}: image {}, digest {}, image file sha256 {}.',
                  'vvvvv'),
    'containers-absent': (SOFT, '- {}: container images are not recorded.', 'va'),
    'citation': (CITE, "Cite GARS at commit {}; the GARS repository's CITATION.cff file gives the "
                       "preferred citation.", 'v'),
    'citation-absent': (CITE, 'The GARS commit to cite is not recorded for workflow {}.', 'va'),
    'record': (READ, '- {}: sha256 {}.', 'r'),
}
MISSING = object()
SOURCE = re.compile(r'- line ([1-9][0-9]*): ([a-z-]+)(?:: `([^`]+)`)?\.\Z')


class TraceError(AssertionError):
    """A rendered line that the records do not account for."""


def o_flat(text):
    return ''.join(' ' if unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp') else c for c in text)


def o_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            for text in o_strings(item):
                yield text
    elif isinstance(value, list):
        for item in value:
            for text in o_strings(item):
                yield text


def o_absent(value):
    if value is MISSING or value is None or value == [] or value == {}:
        return True
    return isinstance(value, str) and not o_flat(value).strip()


def o_span(text):
    runs = [len(r) for r in re.findall('`+', text)]
    fence = '`' * ((max(runs) if runs else 0) + 1)
    if text[:1] == '`' or text[-1:] == '`' or (text[:1] == ' ' and text[-1:] == ' '):
        text = ' ' + text + ' '
    return fence + text + fence


def o_cell(value):
    if o_absent(value):
        return T_NOT
    if any(PATH_LIKE.search(o_flat(s)) for s in o_strings(value)):
        return T_WITHHELD
    text = value if isinstance(value, str) else json.dumps(
        value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return o_span(o_flat(text))


def o_history(text):
    """Entries outside fenced blocks: `## <date> — <stage> — <outcome>`, then Model/Template lines.
    Fences as CommonMark has them: up to three spaces, three or more backticks or tildes (a backtick
    fence's info string holds no backtick), closed only by a run of the same character at least as
    long, with nothing after it but spaces or tabs; an unclosed fence runs to the end."""
    entries, fence, current = [], None, None
    for line in text.split('\n'):
        line = line[:-1] if line.endswith('\r') else line
        if fence is None:
            opening = re.match(r' {0,3}(`{3,}|~{3,})(.*)\Z', line)
            if opening and not (opening.group(1)[0] == '`' and '`' in opening.group(2)):
                fence, current = opening.group(1), None
                continue
        else:
            if re.match(r' {0,3}%s{%d,}[ \t]*\Z' % (re.escape(fence[0]), len(fence)), line):
                fence = None
            continue
        match = re.match(r'## (.+?) \u2014 (.+?) \u2014 (.+?)\s*\Z', line)
        if match:
            current = {'date': match.group(1), 'stage': match.group(2), 'outcome': match.group(3),
                       'model': None, 'template_version': None}
            entries.append(current)
            continue
        if line.startswith('#'):
            current = None
            continue
        if current is not None:
            for field, label in (('model', 'Model: '), ('template_version', 'Template version: ')):
                if line.startswith(label) and current[field] is None:
                    current[field] = line[len(label):].rstrip()
    return entries


class Records(object):
    """The oracle's own reading of the renderer's inputs."""

    def __init__(self, manifests, plan=None, approval=None, history=None):
        self.raw, self.json, self.n = {}, {}, len(manifests)
        for k, path in enumerate(manifests, 1):
            self.raw['manifest%d' % k] = Path(path).read_bytes()
            self.json['manifest%d' % k] = json.loads(self.raw['manifest%d' % k].decode('utf-8'))
        self.plan = self.approval = self.history = None
        if plan is not None:
            self.raw['plan'] = Path(plan).read_bytes()
            self.raw['approval'] = Path(approval).read_bytes()
            self.approval = json.loads(self.raw['approval'].decode('utf-8'))
            self.plan = True
        self.entries = []
        if history is not None:
            self.raw['history'] = Path(history).read_bytes()
            self.entries = o_history(self.raw['history'].decode('utf-8'))
            self.history = True


def o_resolve(rec, ref):
    name, path = ref.split(':', 1)
    if path == 'bytes':
        return hashlib.sha256(rec.raw[name]).hexdigest()
    if name == 'history':
        match = re.fullmatch(r'#(\d+)/(date|stage|outcome|model|template_version)', path)
        if not match:
            raise TraceError('unknown history reference ' + ref)
        value = rec.entries[int(match.group(1))][match.group(2)]
        return MISSING if value is None else value
    node = rec.approval if name == 'approval' else rec.json[name]
    for token in path.strip('/').rstrip('?').split('/'):
        pair = re.fullmatch(r'([a-z_]+)#(\d+)\.(key|value)', token)
        if pair:
            node = node.get(pair.group(1), MISSING) if isinstance(node, dict) else MISSING
            if not isinstance(node, dict) or int(pair.group(2)) >= len(node):
                return MISSING
            key = sorted(node)[int(pair.group(2))]
            node = key if pair.group(3) == 'key' else node[key]
        elif token.isdigit():
            if not isinstance(node, list) or int(token) >= len(node):
                return MISSING
            node = node[int(token)]
        else:
            node = node.get(token, MISSING) if isinstance(node, dict) else MISSING
        if node is MISSING:
            return MISSING
    return node


def o_matches(entry, approval):
    parts = approval.get('plan_path', '').split('/') if isinstance(approval.get('plan_path'), str) else []
    return (len(parts) >= 3 and parts[-1] == 'PLAN.md' and parts[-3] == '03_custom_analysis' and
            entry['stage'] == '03_custom_analysis/' + parts[-2] and entry['outcome'] == 'analysis complete')


def o_expected(rec):
    """The lines a set of records must produce, as (kind, references), in document order: within
    each section, manifests in argument order and each manifest's lines in the specification's order,
    so an "Its …" line and an indented version line stay under the line they belong to."""
    sections = collections.OrderedDict((heading, []) for heading in HEADINGS[:5])

    def add(kind, *refs):
        sections[KINDS[kind][0]].append((kind, refs))

    for k in range(1, rec.n + 1):
        m, M = rec.json['manifest%d' % k], 'manifest%d:' % k
        add('workflow', *(M + p for p in ('/workflow_name', '/workflow_version', '/pipeline_commit',
                                          '/wrapper', '/gars_commit', '/template_version',
                                          '/predicate_facts/status')))
        if not o_absent(m.get('failure_class', MISSING)):
            add('failure', M + '/failure_class')
        reference = m.get('reference', MISSING)
        if o_absent(reference):
            add('reference-absent', M + '/reference')
        else:
            add('reference', *(M + '/reference/' + p for p in ('build', 'annotation_release',
                                                                  'fasta_sha256', 'gtf_sha256')))
            if reference.get('comparison') != 'matched':
                add('reference-check', M + '/reference/comparison', M + '/reference/reason')
        add('config', M + '/config_sha256')
        add('threads', M + '/threads')
        if o_absent(m.get('command', MISSING)):
            add('command-absent', M + '/command')
        else:
            add('command', M + '/command/path', M + '/command/sha256')
        add('agent', M + '/agent_model')
        steps = m.get('model_steps', MISSING)
        if o_absent(steps):
            if m.get('agent_model') != 'none':
                add('model-steps-absent', M + '/model_steps')
        else:
            for i, step in enumerate(steps):
                P = '%s/model_steps/%d' % (M, i)
                prompt = '/prompt_sha256/value' if isinstance(step.get('prompt_sha256'), dict) else '/prompt_sha256'
                add('model-step', P + '/model_id', P + '/provider', P + '/prompt_id', P + prompt)
        params = m.get('params', MISSING)
        if o_absent(params):
            add('params-absent', M + '/workflow_name', M + '/params')
        else:
            for j in range(len(params)):
                add('param', M + '/workflow_name', '%s/params#%d.key' % (M, j), '%s/params#%d.value' % (M, j))
        seeds = m.get('random_seeds', MISSING)
        if o_absent(seeds):
            add('seeds-absent', M + '/workflow_name', M + '/random_seeds')
        elif isinstance(seeds, str):
            add('seeds-text', M + '/workflow_name', M + '/random_seeds')
        else:
            for i, seed in enumerate(seeds):
                P = '%s/random_seeds/%d' % (M, i)
                if o_absent(seed.get('seed', MISSING)):
                    add('seed-unset', M + '/workflow_name', P + '/call', P + '/seed_supported',
                        P + '/determinism', P + '/seed')
                else:
                    add('seed', M + '/workflow_name', P + '/call', P + '/seed')
        add('gars', M + '/gars_commit', M + '/template_version', M + '/workflow_name')
        add('workflow-version', M + '/workflow_name', M + '/workflow_version', M + '/pipeline_commit')
        files = m.get('software_versions', MISSING)
        if o_absent(files):
            add('versions-absent', M + '/workflow_name', M + '/software_versions')
        else:
            for i, entry in enumerate(files):
                P = '%s/software_versions/%d' % (M, i)
                add('versions-file', M + '/workflow_name', P + '/path', P + '/sha256')
                versions = entry.get('versions', MISSING)
                if o_absent(versions):
                    add('version-absent', P + '/versions')
                else:
                    for j in range(len(versions)):
                        add('version', '%s/versions#%d.key' % (P, j), '%s/versions#%d.value' % (P, j))
        containers = m.get('containers', MISSING)
        if o_absent(containers):
            add('containers-absent', M + '/workflow_name', M + '/containers')
        else:
            for i in range(len(containers)):
                P = '%s/containers/%d' % (M, i)
                add('container', M + '/workflow_name', P + '/process', P + '/image', P + '/digest',
                    P + '/image_sha256')
    if rec.plan:   # after every workflow's sentences; the pointer closes the paragraph
        add('approval', 'approval:/plan_sha256', 'approval:/timestamp', 'approval:/actor?')
        if rec.history:
            matches = [e for e, entry in enumerate(rec.entries) if o_matches(entry, rec.approval)]
            for e in matches:
                add('history', *('history:#%d/%s' % (e, f) for f in
                                 ('stage', 'outcome', 'date', 'model', 'template_version')))
            if not matches:
                add('history-absent', 'history:entries', 'approval:/plan_path?')
    add('pointer')
    cited = []
    for k in range(1, rec.n + 1):
        m, M = rec.json['manifest%d' % k], 'manifest%d:' % k
        commit = m.get('gars_commit', MISSING)
        if o_absent(commit):
            add('citation-absent', M + '/workflow_name', M + '/gars_commit')
        elif o_cell(commit) not in cited:
            cited.append(o_cell(commit))
            add('citation', M + '/gars_commit')
    for name in ['manifest%d' % k for k in range(1, rec.n + 1)] + ['plan', 'approval', 'history']:
        if name in rec.raw:
            add('record', name + ':bytes')
    return [line for heading in sections for line in sections[heading]]


def o_line(kind, refs, rec):
    section, template, slots = KINDS[kind]
    if kind == 'record':
        name = refs[0].split(':')[0]
        label = {'plan': 'plan', 'approval': 'approval record', 'history': 'history'}.get(
            name, 'manifest ' + name[len('manifest'):])
        return template.format(label, o_span(o_resolve(rec, refs[0])))
    if len(slots) != len(refs):
        raise TraceError('%s cites %d fields for %d slots' % (kind, len(refs), len(slots)))
    texts = []
    for slot, ref in zip(slots, refs):
        if slot == 'x':
            continue
        value = o_resolve(rec, ref)
        if slot == 'v':
            texts.append(o_cell(value))
        elif slot == 'p':
            texts.append(T_NOBY if o_absent(value) else T_BY)
        elif not o_absent(value):
            raise TraceError('%s says %s is not recorded, and the record holds it' % (kind, ref))
    return template.format(*texts)


def verify(text, rec):
    """Raise TraceError unless every line of `text` is accounted for by `rec`."""
    if not text.endswith('\n') or text.endswith('\n\n'):
        raise TraceError('the output must end with exactly one newline')
    lines = text[:-1].split('\n')
    heads = [i for i, line in enumerate(lines) if line.startswith('#')]
    if [lines[i] for i in heads] != list(HEADINGS) or heads[0] != 0:
        raise TraceError('headings: %r' % [lines[i] for i in heads])
    body = {}
    for h, start in enumerate(heads):
        end = heads[h + 1] if h + 1 < len(heads) else len(lines)
        block = lines[start + 1:end]
        if len(block) < 2 or block[0] != '' or (h + 1 < len(heads) and block[-1] != ''):
            raise TraceError('section %s is not one blank-separated block' % lines[start])
        content = block[1:-1] if h + 1 < len(heads) else block[1:]
        if not content or '' in content:
            raise TraceError('section %s is empty or split' % lines[start])
        for offset, line in enumerate(content):
            body[start + 3 + offset] = (lines[start], line)   # 1-based: heading, blank, then content
    sources = {n: body.pop(n) for n in list(body) if body[n][0] == HEADINGS[-1]}
    cited = {}
    for n, (_, line) in sorted(sources.items()):
        match = SOURCE.match(line)
        if not match or match.group(2) not in KINDS:
            raise TraceError('unreadable Sources line %d: %r' % (n, line))
        number, kind = int(match.group(1)), match.group(2)
        refs = tuple(match.group(3).split(' ')) if match.group(3) else ()
        if number in cited:
            raise TraceError('line %d is cited twice' % number)
        cited[number] = (kind, refs)
    if set(cited) != set(body):
        raise TraceError('uncited lines %s; citations of no line %s' % (
            sorted(set(body) - set(cited)), sorted(set(cited) - set(body))))
    listed = [cited[n] for n in sorted(cited)]   # the lines' own order, whatever order Sources used
    expected = o_expected(rec)
    if listed != expected:
        at = next((i for i, (a, b) in enumerate(zip(listed, expected)) if a != b), min(len(listed), len(expected)))
        raise TraceError('traced line %d of %d: the output has %r where the records call for %r' % (
            at + 1, len(expected), listed[at] if at < len(listed) else None,
            expected[at] if at < len(expected) else None))
    for number, (kind, refs) in cited.items():
        section, line = body[number]
        if section != KINDS[kind][0]:
            raise TraceError('line %d (%s) sits under %s' % (number, kind, section))
        want = o_line(kind, refs, rec)
        if line != want:
            raise TraceError('line %d (%s) reads %r; its fields give %r' % (number, kind, line, want))
    return len(cited)


# ---- helpers ------------------------------------------------------------------------------------

PLAN_DRAFT = (FIXTURE / 'approved-plan.md').read_text(encoding='utf-8').replace(
    'Status: APPROVED 2026-09-29', 'Status: DRAFT')
HEADER = (FIXTURE / 'HISTORY.md').read_text(encoding='utf-8').split('\n## 2026-09-29', 1)[0] + '\n'


class RenderMethodsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='gars-methods-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inputs = self.root / 'inputs'
        shutil.copytree(str(FIXTURE), str(self.inputs))
        self.out = self.root / 'methods.md'

    def path(self, name):
        return self.inputs / name

    def load(self, name):
        return json.loads(self.path(name).read_text(encoding='utf-8'))

    def dump(self, name, value):
        self.path(name).write_text(json.dumps(value, indent=2, sort_keys=True), encoding='utf-8')

    def argv(self, manifests, stage03=True, history=True):
        argv = []
        for name in manifests:
            argv += ['--manifest', str(self.path(name))]
        if stage03:
            argv += ['--plan', str(self.path('approved-plan.md')), '--approval', str(self.path('approval.json'))]
            if history:
                argv += ['--history', str(self.path('HISTORY.md'))]
        return argv + ['--out', str(self.out)]

    def records(self, manifests, stage03=True, history=True):
        return Records([self.path(n) for n in manifests],
                       self.path('approved-plan.md') if stage03 else None,
                       self.path('approval.json') if stage03 else None,
                       self.path('HISTORY.md') if stage03 and history else None)

    def render(self, manifests=('nfcore-manifest.json', 'local-manifest.json'), stage03=True, history=True,
               cli=False):
        argv = self.argv(manifests, stage03, history)
        if cli:
            p = run([sys.executable, CLAIMS / 'render_methods.py'] + argv)
            self.assertEqual(p.returncode, 0, p.stderr.decode())
        else:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(renderer.main(argv), 0, err.getvalue())
        return self.out.read_text(encoding='utf-8')

    def traced(self, manifests=('nfcore-manifest.json', 'local-manifest.json'), stage03=True, history=True):
        text = self.render(manifests, stage03, history)
        verify(text, self.records(manifests, stage03, history))
        self.assertNotIn('UNKNOWN', text)
        return text

    def refuse(self, argv, reason):
        for existing in (False, True):
            if existing:
                self.out.write_bytes(b'previous methods\n')
            elif self.out.exists():
                self.out.unlink()
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = renderer.main(argv)
            self.assertEqual(code, 1, err.getvalue())
            self.assertIn('methods refused: ', err.getvalue())
            self.assertIn(reason, err.getvalue())
            if existing:
                self.assertEqual(self.out.read_bytes(), b'previous methods\n')
            else:
                self.assertFalse(self.out.exists())
        self.out.unlink()
        self.assertEqual([p.name for p in self.root.iterdir() if p.name.startswith('.')], [])

    def in_process(self, argv, patches=()):
        subject = module(CLAIMS / 'render_methods.py', 'methods_in_process')
        with contextlib.ExitStack() as stack:
            for name, value in patches:
                stack.enter_context(mock.patch.object(subject, name, value(subject) if callable(value) else value))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(subject.main(argv), 0)
        return self.out.read_text(encoding='utf-8')

    # ---- 1-3: goldens and the trace -------------------------------------------------------------

    def test_complete_fixture_golden_and_deterministic(self):
        golden = (FIXTURE / 'complete.md').read_bytes()
        self.render(cli=True)
        self.assertEqual(self.out.read_bytes(), golden)
        self.render(cli=True)
        self.assertEqual(self.out.read_bytes(), golden)
        self.render()
        self.assertEqual(self.out.read_bytes(), golden)
        counted = verify(golden.decode('utf-8'), self.records(('nfcore-manifest.json', 'local-manifest.json')))
        text = golden.decode('utf-8')
        self.assertIn('was approved at `2026-09-29T18:04:05Z` by the approver the run recorded.', text)
        self.assertIn('parameter `fasta`: a path-like value, withheld.', text)
        self.assertIn('parameter `formula`: `~ condition`.', text)
        print('complete fixture: %d traced lines' % counted, flush=True)

    def test_sparse_fixture_golden(self):
        golden = (FIXTURE / 'sparse.md').read_bytes()
        self.render(('prepare-manifest.json',), stage03=False, cli=True)
        self.assertEqual(self.out.read_bytes(), golden)
        text = golden.decode('utf-8')
        verify(text, self.records(('prepare-manifest.json',), stage03=False))
        self.assertIn('template version `v0.10.0`; status not recorded.', text)
        self.assertIn('Its reference genome is not recorded.', text)
        self.assertIn('Its agent model is not recorded.', text)
        self.assertNotIn('UNKNOWN', text)
        self.assertNotIn('approv', text)

    def test_every_line_traces_to_a_record_field(self):
        self.traced()
        self.traced(('prepare-manifest.json',), stage03=False)
        self.traced(('local-manifest.json',), history=False)
        m = self.load('nfcore-manifest.json')
        variants = {
            'failed run': dict(m, predicate_facts=dict(m['predicate_facts'], status='FAILED'),
                               failure_class='workflow'),
            'registry mismatch': dict(m, reference=dict(m['reference'], comparison='mismatch',
                                                        reason='reference_hash_mismatch')),
            'registry check without reason': dict(m, reference={'build': 'fixture-build', 'comparison': None}),
            'no model-mediated step': dict(m, agent_model='none', model_steps=[]),
            'a mutable tag': dict(m, containers=m['containers'] + [{'process': 'MUTABLE',
                                                                   'image': 'fixture/tool:latest'}]),
            'a string prompt hash': dict(m, model_steps=[dict(m['model_steps'][0], prompt_sha256='d' * 40)]),
            'string random seeds': dict(m, random_seeds='no-rng-in-code-path'),
            'several versions files': dict(m, software_versions=m['software_versions'] + [
                {'path': 'run/versions.json', 'sha256': 'e' * 64, 'versions': {}}]),
        }
        for label, variant in variants.items():
            with self.subTest(variant=label):
                self.dump('variant.json', variant)
                text = self.traced(('variant.json', 'nfcore-manifest.json'))
                if label == 'a mutable tag':
                    self.assertIn('container for process `MUTABLE`: image `fixture/tool:latest`, digest '
                                  'not recorded, image file sha256 not recorded.', text)
                if label == 'no model-mediated step':
                    self.assertIn('Its agent model is `none`.', text)
                if label == 'registry mismatch':
                    self.assertIn('Its reference registry check reads `mismatch`, reason '
                                  '`reference_hash_mismatch`.', text)
        # The producers write sorted keys; a record whose file order is not sorted must still be
        # rendered, and cited, in sorted-key order.
        unsorted = copy.deepcopy(m)
        unsorted['params'] = dict(reversed(sorted(m['params'].items())))
        unsorted['software_versions'][0]['versions'] = {'z-tool': '2', 'a-tool': '1'}
        self.path('variant.json').write_text(json.dumps(unsorted, indent=2), encoding='utf-8')
        text = self.traced(('variant.json',))
        self.assertLess(text.index('parameter `aligner`'), text.index('parameter `outdir`'))
        self.assertLess(text.index('`a-tool`: `1`.'), text.index('`z-tool`: `2`.'))

    # ---- 4: the mutation proof ------------------------------------------------------------------

    def test_an_invented_value_is_caught(self):
        complete = self.render()
        rec = self.records(('nfcore-manifest.json', 'local-manifest.json'))
        verify(complete, rec)
        lines = complete.split('\n')

        def plant(old, new, text=complete):
            self.assertEqual(text.count(old), 1, old)
            return text.replace(old, new)

        with self.assertRaises(TraceError):   # (a) a record value changed
            verify(plant('records: version `3.26.0`;', 'records: version `3.27.0`;'), rec)
        sparse = self.render(('prepare-manifest.json',), stage03=False)
        sparse_rec = self.records(('prepare-manifest.json',), stage03=False)
        with self.assertRaises(TraceError):   # (b) "not recorded" replaced by a plausible value
            verify(plant('; status not recorded.', '; status `COMPLETE`.', sparse), sparse_rec)
        # (c) a free sentence, with the Sources renumbered as a careful forger would
        at = lines.index('## Parameters') - 1
        forged = lines[:at] + ['All samples passed quality control.'] + lines[at:]
        forged = [re.sub(r'^- line (\d+):', lambda m: '- line %d:' % (int(m.group(1)) + (int(m.group(1)) > at)), l)
                  for l in forged]
        with self.assertRaises(TraceError):
            verify('\n'.join(forged), rec)
        # (d) a Sources line removed
        dropped = [l for l in lines if not l.startswith('- line 3: ')]
        self.assertEqual(len(dropped), len(lines) - 1)
        with self.assertRaises(TraceError):
            verify('\n'.join(dropped), rec)
        # (e) the approval time taken from the expiry, and cited from it
        approval = self.load('approval.json')
        moved = plant('approved at `%s`' % approval['timestamp'], 'approved at `%s`' % approval['expiry'])
        moved = moved.replace('approval:/plan_sha256 approval:/timestamp approval:/actor?',
                              'approval:/plan_sha256 approval:/expiry approval:/actor?')
        with self.assertRaises(TraceError):
            verify(moved, rec)
        # (g) two workflows' "Its configuration sha256" lines swapped, each still citing its own
        # field, so every line alone is right and only its place is wrong (review r1 F-3)
        def swap(a, b, kind):
            out = list(lines)
            out[a], out[b] = lines[b], lines[a]
            numbers = {'- line %d: %s:' % (a + 1, kind): '- line %d: %s:' % (b + 1, kind),
                       '- line %d: %s:' % (b + 1, kind): '- line %d: %s:' % (a + 1, kind)}
            out = [next((l.replace(o, n) for o, n in numbers.items() if l.startswith(o)), l) for l in out]
            self.assertEqual(sum(1 for x, y in zip(out, lines) if x != y), 4)   # two lines, two citations
            return '\n'.join(out)

        a, b = [i for i, l in enumerate(lines) if l.startswith('Its configuration sha256 is ')]
        with self.assertRaises(TraceError):
            verify(swap(a, b, 'config'), rec)
        # ... and a tool version moved under the other workflow's versions file
        a = lines.index('  - `FIXTURE_PROCESS/fixture-tool`: `1.0.0`.')
        b = lines.index('  - `pandas`: `fixture-1`.')
        with self.assertRaises(TraceError):
            verify(swap(a, b, 'version'), rec)
        # (f) the renderer itself mutated: a guessed default, then an invented version
        argv = self.argv(('prepare-manifest.json',), stage03=False)
        guessed = self.in_process(argv, [('NOT_RECORDED', 'GRCh38')])
        self.assertIn('GRCh38', guessed)
        with self.assertRaises(TraceError):
            verify(guessed, sparse_rec)

        def inventing(subject):
            original = subject.cell

            def cell(value):
                text = original(value)
                return '`v0.11.0`' if text == '`v0.10.0`' else text
            return cell
        invented = self.in_process(argv, [('cell', inventing)])
        self.assertIn('`v0.11.0`', invented)
        with self.assertRaises(TraceError):
            verify(invented, sparse_rec)
        self.assertEqual(self.in_process(argv), sparse)   # the unmutated control

    # ---- 5-6: absence and paths -----------------------------------------------------------------

    def test_missing_and_empty_values_read_not_recorded(self):
        base = self.load('nfcore-manifest.json')
        fields = [('workflow_name',), ('workflow_version',), ('pipeline_commit',), ('wrapper',),
                  ('gars_commit',), ('template_version',), ('predicate_facts', 'status'),
                  ('predicate_facts',), ('reference', 'build'), ('reference', 'annotation_release'),
                  ('reference', 'fasta_sha256'), ('reference', 'gtf_sha256'), ('reference',),
                  ('config_sha256',), ('threads',), ('command', 'path'), ('command', 'sha256'),
                  ('command',), ('agent_model',), ('model_steps', 0, 'model_id'),
                  ('model_steps', 0, 'provider'), ('model_steps', 0, 'prompt_id'),
                  ('model_steps', 0, 'prompt_sha256', 'value'), ('model_steps', 0, 'prompt_sha256'),
                  ('model_steps',), ('params', 'aligner'), ('params',), ('random_seeds',),
                  ('software_versions', 0, 'path'), ('software_versions', 0, 'sha256'),
                  ('software_versions', 0, 'versions', 'FIXTURE_PROCESS/fixture-tool'),
                  ('software_versions', 0, 'versions'), ('software_versions',),
                  ('containers', 0, 'process'), ('containers', 0, 'image'), ('containers', 0, 'digest'),
                  ('containers', 1, 'image_sha256'), ('containers',)]
        for path in fields:
            for empty in ('delete', None, '', ' \t\n', [], {}):
                with self.subTest(field='.'.join(map(str, path)), empty=empty):
                    manifest = copy.deepcopy(base)
                    target = manifest
                    for key in path[:-1]:
                        target = target[key]
                    if empty == 'delete':
                        del target[path[-1]]
                    else:
                        target[path[-1]] = empty
                    self.dump('variant.json', manifest)
                    text = self.traced(('variant.json',))
                    self.assertIn(T_NOT, text)
        approval = self.load('approval.json')
        for empty in ('delete', None, '', []):
            with self.subTest(field='approval timestamp', empty=empty):
                changed = dict(approval)
                if empty == 'delete':
                    del changed['timestamp']
                else:
                    changed['timestamp'] = empty
                self.dump('approval.json', changed)
                self.assertIn('was approved at not recorded by the approver the run recorded.',
                              self.traced(('local-manifest.json',)))
        self.dump('approval.json', approval)

    def test_local_paths_are_never_printed(self):
        complete = self.traced()
        self.assertNotIn('/fixture-workspace', complete)
        self.assertIn('parameter `aligner`: `star_salmon`.', complete)
        m = self.load('local-manifest.json')
        hostile = ['/abs/secret', '~/home-secret', '~someone/secret', '\\\\server\\share', 'C:\\data\\x',
                   'd:/data/x', 'file:///etc/x', 'FILE:x', '--outdir=/abs/secret', 'a /abs/secret',
                   '"/quoted/abs"', '{"nested": "/abs/secret"}', 'x;/abs', '(/abs)', 'line\n/abs',
                   'user@host:/abs/secret', 'cat x >/abs/secret', 'a|/abs/secret', 'key:/abs/secret',
                   'x&/abs/secret', 'a+/abs/secret', 'tab\t/abs/secret']
        for value in hostile:
            with self.subTest(value=value):
                changed = dict(m, params={'p': value, value: 'key-side', 'nested': {'deep': [value]}},
                               containers=[{'process': 'P', 'image': value, 'image_sha256': 'f' * 64}],
                               command={'path': value, 'sha256': 'c' * 64},
                               workflow_version=[value])
                self.dump('variant.json', changed)
                text = self.traced(('variant.json',), stage03=False)
                self.assertNotIn(value, text)
                self.assertNotIn('secret', text)
                self.assertNotIn('/abs', text)
                self.assertIn('parameter `p`: a path-like value, withheld.', text)
                self.assertIn('parameter `nested`: a path-like value, withheld.', text)
                self.assertIn('parameter a path-like value, withheld: `key-side`.', text)
        for value in ('~ condition', 'condition,MT,WT', 'quay.io/biocontainers/fastqc:0.12.1',
                      'https://depot.galaxyproject.org/singularity/fastqc', 'pipeline_info/fixture.sif',
                      'N/A', 'sha256:' + 'a' * 64, 's3://bucket/key', 'quay.io:443/biocontainers/fastqc',
                      './relative/x', '../relative/x', '$HOME/x', 'a\\b', 'fixture/tool@sha256:' + 'b' * 64):
            with self.subTest(shown=value):
                self.dump('variant.json', dict(m, params={'p': value}))
                self.assertIn('parameter `p`: `%s`.' % value, self.traced(('variant.json',), stage03=False))

    # ---- 7-8: the approval and the history ------------------------------------------------------

    def test_approval_binds_the_plan_and_never_names_the_actor(self):
        text = self.traced()
        self.assertNotIn('fixture-operator', text)
        self.assertNotIn('fixture-workspace', text)
        approval = self.load('approval.json')
        argv = self.argv(('local-manifest.json',))
        plan = self.path('approved-plan.md').read_bytes()
        self.path('approved-plan.md').write_bytes(plan + b'\nEdited after approval.\n')
        self.refuse(argv, 'approval record does not bind this plan')
        self.path('approved-plan.md').write_bytes(plan)
        for bad, reason in (({'plan_sha256': None}, 'approval record has no plan_sha256'),
                            ({'plan_sha256': approval['plan_sha256'].upper()}, 'plan_sha256 is not 64 hex digits'),
                            ({'plan_sha256': 'abc'}, 'plan_sha256 is not 64 hex digits'),
                            ({'timestamp': '2026-09-29 18:04:05'}, 'timestamp is not a UTC instant'),
                            ({'timestamp': '2026-13-29T18:04:05Z'}, 'timestamp is not a UTC instant'),
                            ({'timestamp': '2026-09-29T18:04:05+00:00'}, 'timestamp is not a UTC instant'),
                            ({'timestamp': 20260929}, 'timestamp is not a UTC instant'),
                            ({'actor': 1}, 'actor is not a string'),
                            ({'actor': ['fixture-operator']}, 'actor is not a string')):
            with self.subTest(bad=bad):
                self.dump('approval.json', dict(approval, **bad))
                self.refuse(argv, reason)
        for actor in ('delete', None, '', '   '):
            with self.subTest(actor=actor):
                changed = dict(approval)
                if actor == 'delete':
                    del changed['actor']
                else:
                    changed['actor'] = actor
                self.dump('approval.json', changed)
                self.assertIn('with no approver named in its approval record.', self.traced(('local-manifest.json',)))
        self.dump('approval.json', dict(approval, actor='someone-else'))
        text = self.traced(('local-manifest.json',))
        self.assertIn(T_BY, text)
        self.assertNotIn('someone-else', text)

    def test_history_names_only_the_approved_analysis(self):
        history = self.path('HISTORY.md').read_text(encoding='utf-8')
        entry = history.split('\n## 2026-09-29 \u2014 03_custom_analysis/')[1]
        fenced = ('```\n## 2026-09-29 \u2014 03_custom_analysis/01_fixture-followup \u2014 analysis complete\n'
                  'Model: fenced-model\n```\n')
        other = ('\n## 2026-09-30 \u2014 03_custom_analysis/02_other \u2014 analysis complete\n\n'
                 'Model: other-model\n')
        failed = ('\n## 2026-09-30 \u2014 03_custom_analysis/01_fixture-followup \u2014 analysis failed\n\n'
                  'Model: failed-model\n')
        again = '\n## 2026-10-01 \u2014 03_custom_analysis/' + entry.replace('claude-opus-5-5', 'second-model')
        inside = ('## 2026-10-02 \u2014 03_custom_analysis/01_fixture-followup \u2014 analysis complete\n'
                  'Template version: v0.10.0\nModel: %s\n')
        cases = {
            'a four-backtick fence': (history + '\n````\n```\n' + inside % 'inside-four' + '```\n````\n',
                                      ['claude-opus-5-5'], ['inside-four']),
            'a tilde fence': (history + '\n~~~~\n' + inside % 'inside-tilde' + '~~~~~\n',
                              ['claude-opus-5-5'], ['inside-tilde']),
            'an info string does not close': (history + '\n```\n```python\n' + inside % 'inside-info' + '```\n',
                                              ['claude-opus-5-5'], ['inside-info']),
            'an unclosed fence': (history + '\n  ```text\n' + inside % 'inside-unclosed',
                                  ['claude-opus-5-5'], ['inside-unclosed']),
            'a four-space line is not a fence': (history + '\n    ```\n' + inside % 'after-indented' + '    ```\n',
                                                 ['claude-opus-5-5', 'after-indented'], []),
            'a backtick in the info string opens no fence': (history + '\n```not`a fence\n' + inside % 'after-info',
                                                             ['claude-opus-5-5', 'after-info'], []),
            'as recorded': (history, ['claude-opus-5-5'], []),
            'a fenced look-alike': (history + '\n' + fenced, ['claude-opus-5-5'], ['fenced-model']),
            'another analysis': (history + other + failed, ['claude-opus-5-5'], ['other-model', 'failed-model']),
            'recorded twice': (history + again, ['claude-opus-5-5', 'second-model'], []),
            'not recorded': (HEADER, [], []),
            'no model line': (history.replace('Model: claude-opus-5-5\nPlan:', 'Plan:'), [], []),
            'two model lines': (history.replace('Model: claude-opus-5-5\nPlan:',
                                                'Model: claude-opus-5-5\nModel: second-line-model\nPlan:'),
                                ['claude-opus-5-5'], ['second-line-model']),
        }
        for label, (text, shown, hidden) in cases.items():
            with self.subTest(case=label):
                self.path('HISTORY.md').write_text(text, encoding='utf-8')
                rendered = self.traced(('local-manifest.json',))
                lines = [l for l in rendered.split('\n') if l.startswith("The project's history records ")]
                self.assertEqual(len(lines), len(shown) + (label == 'no model line'))
                for model in shown:
                    self.assertIn('with model `%s` and template version `v0.10.0`.' % model, rendered)
                for model in hidden:
                    self.assertNotIn(model, rendered)
                if label == 'not recorded':
                    self.assertIn("The approved analysis's completion is not recorded in the project's history.",
                                  rendered)
                if label == 'no model line':
                    self.assertIn('with model not recorded and template version `v0.10.0`.', rendered)
        self.dump('approval.json', dict(self.load('approval.json'), plan_path='PLAN.md'))
        self.path('HISTORY.md').write_text(history, encoding='utf-8')
        self.assertIn("completion is not recorded", self.traced(('local-manifest.json',)))

    # ---- 9-11: structure, refusals, isolation ---------------------------------------------------

    def test_hostile_values_cannot_add_structure(self):
        m = self.load('local-manifest.json')
        hostile = ['a`b', '``x``', '`lead', 'trail`', ' both ', ' `both` ', 'line\nbreak',
                   'para\u2029sep', 'line\u2028sep', 'cr\rreturn', 'nel\x85line', 'tab\there', '## invented',
                   '<script>alert(1)</script>', 'a|b|c', 'bidi\u202eevil', 'zero\u200bwidth',
                   'nul\x00byte', '- a list', '1. a list', '===', '> quote', '\ud800lone']
        history = self.path('HISTORY.md')
        saved = history.read_text(encoding='utf-8')
        for value in hostile:
            with self.subTest(value=value):
                changed = dict(m, workflow_name=value, params={value: value},
                               software_versions=[{'path': value, 'sha256': value, 'versions': {value: value}}],
                               containers=[{'process': value, 'image': value}], agent_model=value)
                self.dump('variant.json', changed)
                # A text file cannot hold a lone surrogate or break a line inside one entry field.
                model = value.replace('\n', ' ').replace('\r', ' ').replace('\ud800', '?')
                history.write_text(saved.replace('Model: claude-opus-5-5\nPlan:', 'Model: ' + model + '\nPlan:'),
                                   encoding='utf-8')
                text = self.traced(('variant.json',))
                self.assertEqual([l for l in text.split('\n') if l.startswith('#')], list(HEADINGS))
                for character in ('\r', '\x85', '\u2028', '\u2029', '\u202e', '\u200b', '\x00'):
                    self.assertNotIn(character, text)

    def test_refusals_preserve_existing_output(self):
        manifest = self.path('local-manifest.json')
        good = manifest.read_bytes()
        argv = self.argv(('local-manifest.json',))
        for payload, reason in ((b'\xff\xfe', 'manifest 1 is not UTF-8'),
                                (b'{', 'manifest 1 is not valid JSON'),
                                (b'{"a": 1, "a": 2}', 'manifest 1 repeats the key'),
                                (b'{"a": NaN}', 'manifest 1 holds a non-finite number'),
                                (b'{"a": Infinity}', 'manifest 1 holds a non-finite number'),
                                (b'{"threads": 1e400}', 'manifest 1 holds a non-finite number'),
                                (b'{"params": {"x": [-1E999]}}', 'manifest 1 holds a non-finite number'),
                                (b'{"params": {"p": ' + b'[' * 3000 + b']' * 3000 + b'}}',
                                 'manifest 1 is nested too deeply'),
                                (b'[]', 'manifest 1 is not a JSON object'),
                                (b'"text"', 'manifest 1 is not a JSON object')):
            with self.subTest(payload=payload):
                manifest.write_bytes(payload)
                self.refuse(argv, reason)
        manifest.write_bytes(good)
        m = json.loads(good.decode('utf-8'))
        for change, reason in (({'params': ['a']}, 'params must be a JSON object'),
                               ({'params': 'text'}, 'params must be a JSON object'),
                               ({'reference': 'GRCh38'}, 'reference must be a JSON object'),
                               ({'command': ['x']}, 'command must be a JSON object'),
                               ({'predicate_facts': ['COMPLETE']}, 'predicate_facts must be a JSON object'),
                               ({'model_steps': {'a': 1}}, 'model_steps must be a JSON array'),
                               ({'model_steps': ['x']}, 'model_steps[0] must be a JSON object'),
                               ({'containers': 'image'}, 'containers must be a JSON array'),
                               ({'containers': [1]}, 'containers[0] must be a JSON object'),
                               ({'software_versions': [[]]}, 'software_versions[0] must be a JSON object'),
                               ({'software_versions': [{'versions': ['x']}]},
                                'software_versions[0].versions must be a JSON object'),
                               ({'random_seeds': {'call': 'x'}}, 'random_seeds must be a JSON array or string'),
                               ({'random_seeds': ['x']}, 'random_seeds[0] must be a JSON object')):
            with self.subTest(change=change):
                self.dump('local-manifest.json', dict(m, **change))
                self.refuse(argv, reason)
        manifest.write_bytes(good)
        approval = self.path('approval.json').read_bytes()
        self.path('approval.json').write_bytes(b'[]')
        self.refuse(argv, 'approval record is not a JSON object')
        self.path('approval.json').write_bytes(b'{"actor": 1, "actor": 2}')
        self.refuse(argv, 'approval record repeats the key')
        self.path('approval.json').write_bytes(approval)
        self.path('HISTORY.md').write_bytes(b'\xff')
        self.refuse(argv, 'history is not UTF-8')
        missing = self.argv(('absent-manifest.json',), stage03=False)
        self.refuse(missing, 'cannot read manifest 1')
        folder = ['--manifest', str(self.inputs)] + missing[2:]
        self.refuse(folder, 'cannot read manifest 1')
        p = run([sys.executable, CLAIMS / 'render_methods.py'] + missing)   # the real command line
        self.assertEqual(p.returncode, 1, p.stderr.decode())
        self.assertIn('methods refused: cannot read manifest 1', p.stderr.decode())
        self.assertFalse(self.out.exists())
        self.path('HISTORY.md').write_bytes((FIXTURE / 'HISTORY.md').read_bytes())
        for index, role in ((1, 'manifest 1'), (3, 'plan'), (5, 'approval record'), (7, 'history')):
            with self.subTest(overwrite=role):
                target = Path(argv[index])
                before = target.read_bytes()
                onto = argv[:-1] + [str(self.inputs / '.' / target.name)]   # the same file, spelled apart
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertEqual(renderer.main(onto), 1)
                self.assertIn('methods refused: the output would overwrite ' + role, err.getvalue())
                self.assertEqual(target.read_bytes(), before)

    def test_only_named_inputs_are_opened(self):
        approval = self.load('approval.json')
        decoy = self.root / 'decoy' / '03_custom_analysis' / '01_fixture-followup' / 'PLAN.md'
        decoy.parent.mkdir(parents=True)
        decoy.write_bytes(self.path('approved-plan.md').read_bytes())
        self.dump('approval.json', dict(approval, plan_path=str(decoy)))
        argv = self.argv(('nfcore-manifest.json', 'local-manifest.json'))
        allowed = {self.path(n).resolve() for n in ('nfcore-manifest.json', 'local-manifest.json', 'approved-plan.md',
                                                    'approval.json', 'HISTORY.md')}
        reads = []
        real_open, real_io_open, real_os_open = builtins.open, io.open, os.open

        def guarded(opener):
            def opening(path, mode='r', *args, **kwargs):
                if isinstance(path, (str, bytes, Path)) and ('r' in mode or '+' in mode):
                    resolved = Path(os.fsdecode(path) if isinstance(path, bytes) else path).resolve()
                    self.assertIn(resolved, allowed, 'renderer opening an unnamed file: %s' % resolved)
                    reads.append(resolved)
                return opener(path, mode, *args, **kwargs)
            return opening

        def guarded_os_open(path, flags, *args, **kwargs):
            if not flags & os.O_WRONLY and not flags & os.O_CREAT:
                resolved = Path(os.fsdecode(path)).resolve()
                self.assertIn(resolved, allowed, 'renderer opening an unnamed file: %s' % resolved)
                reads.append(resolved)
            return real_os_open(path, flags, *args, **kwargs)

        subject = module(CLAIMS / 'render_methods.py', 'methods_isolation')
        with mock.patch('builtins.open', guarded(real_open)), mock.patch('io.open', guarded(real_io_open)), \
                mock.patch('os.open', guarded_os_open):
            self.assertEqual(subject.main(argv), 0)
        self.assertEqual(set(reads), allowed)
        self.assertNotIn(str(decoy), self.out.read_text(encoding='utf-8'))

    # ---- 12-14: the fixtures and the real producers ---------------------------------------------

    def test_fixture_shapes_match_the_producers(self):
        import manifest_check
        for name in ('nfcore-manifest.json', 'local-manifest.json'):
            self.assertTrue(manifest_check.grade(self.load(name))['ok'], name)
        with self.assertRaisesRegex(ValueError, 'predicate_facts'):   # prepare-only: collect never ran
            manifest_check.grade(self.load('prepare-manifest.json'))
        source = (GARS / '_system/stage03_analysis.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        keys = None
        for node in ast.walk(functions['cmd_approve']):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict) and
                    [getattr(t, 'id', None) for t in node.targets] == ['record']):
                keys = {ast.literal_eval(k) for k in node.value.keys}
        self.assertEqual(keys, set(self.load('approval.json')))
        strings = set()
        for n in ast.walk(functions['cmd_verify']):   # ast.Str before Python 3.8, ast.Constant after
            if type(n).__name__ == 'Str':
                strings.add(n.s)
            elif type(n).__name__ == 'Constant' and isinstance(n.value, str):
                strings.add(n.value)
        entry = self.path('HISTORY.md').read_text(encoding='utf-8').split('\n## 2026-09-29 \u2014 03_')[1]
        for template in ('## <ISO-8601 date> \u2014 03_custom_analysis/%s \u2014 analysis complete',
                         'Template version: %s', 'Model: %s', 'Plan: %s/%s/PLAN.md (approved%s)'):
            self.assertIn(template, strings)
        self.assertIn('\nTemplate version: v0.10.0\nModel: claude-opus-5-5\n'
                      'Plan: 03_custom_analysis/01_fixture-followup/PLAN.md (approved 2026-09-29)\n', entry)
        self.assertEqual(hashlib.sha256(self.path('approved-plan.md').read_bytes()).hexdigest(),
                         self.load('approval.json')['plan_sha256'])

    def test_real_collect_manifest_renders_traced(self):
        groups = module(GARS / 'tests/test_manifest_groups.py', 'methods_manifest_groups')
        case = groups.ManifestGroupsTests('test_rnaseq_de_cold_start_and_idempotent_collect')
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.prepare()
        case.fake_run()
        case.submit()
        case.collect()
        shutil.copyfile(str(case.manifest_path), str(self.path('live.json')))
        text = self.traced(('live.json',), stage03=False)
        self.assertNotIn(str(case.fixture.tmp), text)
        self.assertNotIn(str(Path(tempfile.gettempdir())), text)
        self.assertIn('Its agent model is `claude-opus-5-5`.', text)
        self.assertIn('random seed for `sklearn.decomposition.PCA`: `0`.', text)

    def test_real_approval_and_history_render_traced(self):
        import executorlib as ex
        import stage03_analysis as stage
        workspace = self.root / 'workspace'
        workspace.mkdir()
        (workspace / '_references').symlink_to(GARS / '_references', target_is_directory=True)
        project = workspace / 'projects/p'
        write_fixture_dataset(project)
        adir = project / '03_custom_analysis/01_methods'
        (adir / 'results').mkdir(parents=True)
        (adir / 'results/table.tsv').write_text('a\tb\n1\t2\n')
        (adir / 'PLAN.md').write_text(PLAN_DRAFT)
        (adir / 'run').mkdir()
        (adir / 'run/.gars_run_complete').write_text('synthetic successful execution\n')
        script, launcher = adir / 'script.sh', adir / 'run/launcher.sh'
        script.write_text('exit 0\n')
        launcher.write_text('exit 0\n')
        (adir / ex.ANALYSIS_SUBMISSIONS).write_text(json.dumps({
            'script': str(script), 'script_sha256': ex._sha256(script), 'launcher': str(launcher),
            'launcher_sha256': ex._sha256(launcher), 'job_id': 'fixture', 'executor': 'local',
            'submitted_at': 1}) + '\n')
        jobs = ex._local_jobs_dir(project)
        jobs.mkdir()
        exit_file = adir / 'run/launcher.sh.local.exit'
        exit_file.write_text('0')
        (jobs / 'fixture.json').write_text(json.dumps({'script': str(launcher), 'exit_file': str(exit_file)}))
        args = argparse.Namespace(project=str(project), analysis='01_methods', model='claude-opus-5-5', date=None)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(stage.cmd_approve(args, workspace), 0)
        verified = io.StringIO()
        with contextlib.redirect_stdout(verified):
            self.assertEqual(stage.cmd_verify(args, workspace), 0)
        entry = json.loads(verified.getvalue())['history_entry'].replace('<ISO-8601 date>', '2026-09-29')
        self.path('HISTORY.md').write_text(HEADER + '\n' + entry + '\n', encoding='utf-8')
        shutil.copyfile(str(adir / 'PLAN.md'), str(self.path('approved-plan.md')))
        shutil.copyfile(str(stage.approval_record_path(adir / 'PLAN.md', workspace)), str(self.path('approval.json')))
        text = self.traced(('local-manifest.json',))
        self.assertIn(T_BY, text)
        self.assertIn('records `03_custom_analysis/01_methods` as `analysis complete` on `2026-09-29`, '
                      'with model `claude-opus-5-5`', text)
        actor = pwd.getpwuid(os.getuid()).pw_name
        self.assertEqual(self.load('approval.json')['actor'], actor)   # the real record names the OS user
        self.assertNotIn('`%s`' % actor, text)
        self.assertNotIn(str(workspace), text)
        self.assertNotIn(self.load('approval.json')['plan_path'], text)

    # ---- 15-16: the command line and the code ---------------------------------------------------

    def test_cli_usage_and_exit_codes(self):
        base = ['--manifest', str(self.path('local-manifest.json')), '--out', str(self.out)]
        for extra in (['--approval', str(self.path('approval.json'))],
                      ['--plan', str(self.path('approved-plan.md'))],
                      ['--history', str(self.path('HISTORY.md'))],
                      ['--plan', str(self.path('approved-plan.md')), '--history', str(self.path('HISTORY.md'))]):
            with self.subTest(extra=extra):
                p = run([sys.executable, CLAIMS / 'render_methods.py'] + base + extra)
                self.assertEqual(p.returncode, 2, p.stderr.decode())
                self.assertFalse(self.out.exists())
        p = run([sys.executable, CLAIMS / 'render_methods.py', '--out', str(self.out)])
        self.assertEqual(p.returncode, 2)
        p = run([sys.executable, CLAIMS / 'render_methods.py'] + base)
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        # The page is written to be shared: a new page takes the umask's mode, not a temp file's
        # 0600, and a re-render keeps the mode the owner gave it (review r1 F-8).
        umask = os.umask(0)
        os.umask(umask)
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o666 & ~umask)
        self.out.chmod(0o640)
        p = run([sys.executable, CLAIMS / 'render_methods.py'] + base)
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o640)

    def test_stdlib_only_and_python36_parseable(self):
        source = (CLAIMS / 'render_methods.py').read_text(encoding='utf-8')
        if sys.version_info >= (3, 8):
            tree = ast.parse(source, feature_version=(3, 6))
        else:
            tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or '').split('.')[0])
        allowed = {'argparse', 'datetime', 'hashlib', 'json', 'os', 'pathlib', 're', 'sys', 'tempfile',
                   'unicodedata'}
        self.assertLessEqual(imported, allowed)
        self.assertIn('json', imported)


if __name__ == '__main__':
    unittest.main(verbosity=2)
