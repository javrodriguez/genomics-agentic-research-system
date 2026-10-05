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
# Right after a colon, ~/, ~user/ (user@host:~user/x) and a drive letter (x:C:\x) start a path as a
# lone slash does; a lone backslash there does not (pattern:\d+ is shown).
# A URL with an empty authority (x:///etc) names a local path too. No re.I: with it, [A-Za-z]
# would also match letters that case-fold to ASCII (the Kelvin sign), and this rule is ASCII.
PATH_LIKE = re.compile(r'''(?<![A-Za-z0-9._~/:\\-])(?:/|~[^\s/"']*/|\\|[A-Za-z]:[\\/])'''
                       r'''|(?<=:)(?:/(?!/)|///|~[^\s/"']*/|[A-Za-z]:[\\/])'''
                       r'''|(?<![A-Za-z0-9])[Ff][Ii][Ll][Ee]:'''
                       # a storage URI: its bucket name can hold the cloud account id (0276)
                       r'''|(?<![-A-Za-z0-9+.])(?:[Ss]3[AaNn]?|[Gg][Ss]|[Gg][Cc][Ss]|[Aa][Zz]|[Aa][Bb][Ff][Ss][Ss]?'''
                       r'''|[Ww][Aa][Ss][Bb][Ss]?|[Ff][Ii][Ll][Ee])://''')
HEADINGS = ('# Methods', '## Provenance', '### Parameters', '### Software used', '### Citation',
            '### Records read', '### Sources')
METHODS, PARA, PARAM, SOFT, CITE, READ = HEADINGS[:6]
# Provenance kinds (0236; under Provenance since 0276).
# kind: (section heading, fixed text, slot types) -- v value, p approver phrase, a absent, x unprinted
KINDS = {
    'workflow': (PARA, 'The run manifest of workflow {} records: version {}; pipeline commit {}; '
                       'GARS wrapper {}; GARS commit {}; template version {}; status {}.', 'vvvvvvv'),
    'failure': (PARA, 'Its failure class is {}.', 'v'),
    'reference': (PARA, 'Its reference genome: build {}; annotation release {}; '
                        'FASTA sha256 {}; GTF sha256 {}.', 'vvvv'),
    'reference-check': (PARA, 'Its reference registry check reads {}, reason {}; the run observed '
                              'FASTA sha256 {} and GTF sha256 {}.', 'vvvv'),
    'reference-absent': (PARA, 'Its reference genome is not recorded.', 'a'),
    'config': (PARA, 'Its configuration sha256 is {}.', 'h'),
    'threads': (PARA, 'Its thread count is {}.', 'v'),
    'command': (PARA, 'Its exact submission: {}, sha256 {}.', 'vh'),
    'command-absent': (PARA, 'Its exact submission is not recorded.', 'a'),
    'agent': (PARA, 'Its agent model is {}.', 'v'),
    'model-step': (PARA, 'It records a model-mediated step: model {}; provider {}; contract {}; '
                         'contract hash {} (algorithm {}).', 'vvvvv'),
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
    'record-unpublished': (READ, '- {}: sha256 not published, since the record holds values this page does not '
                                 'print.', 'r'),
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
    sections = collections.OrderedDict((heading, []) for heading in HEADINGS[:6])

    def add(kind, *refs):
        sections[KINDS[kind][0]].append((kind, refs))

    for line in o_prose_expected(rec):
        sections[METHODS].append(line)
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
                add('reference-check', M + '/reference/comparison', M + '/reference/reason',
                    M + '/reference/observed/fasta_sha256', M + '/reference/observed/gtf_sha256')
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
                add('model-step', P + '/model_id', P + '/provider', P + '/prompt_id', P + prompt,
                    P + '/prompt_sha256/algorithm')
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
            if o_hides(rec, name):
                add('record-unpublished', name + ':withheld')
            else:
                add('record', name + ':bytes')
    return [line for heading in sections for line in sections[heading]]


# ---- the oracle: the journal paragraph's frames (0276), restated --------------------------------
# A clause is shown only when its field is recorded and shown; a dropped clause leaves no words and
# no reference. Plain words are ASCII letters and digits joined singly by . _ + : / -, not starting
# with www.; any other shown value, and any number or boolean, is a code span. Each frame below is
# the specification's, written again here.

PROSE = ('prose-run', 'prose-configured', 'prose-agent-all', 'prose-agent', 'prose-agent-none',
         'prose-approval', 'prose-history', 'prose-closing')
P_NO_NAME = 'a workflow whose name is not recorded'
P_HIDDEN_NAME = 'a workflow whose recorded name is withheld'
P_CLOSING = ("Parameters, software versions and container images are listed below, or marked not recorded; "
             "every value traces to the run's records (Provenance).")
P_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
            'November', 'December']
P_PLAIN = r'[A-Za-z0-9]+(?:[._+:/-][A-Za-z0-9]+)*'


def o_plain(text):
    return re.fullmatch(P_PLAIN, text) is not None and not text.lower().startswith('www.')


def o_words(value):
    if o_absent(value) or any(PATH_LIKE.search(o_flat(s)) for s in o_strings(value)):
        return None
    if not isinstance(value, str):
        return o_span(o_flat(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)))
    return value if o_plain(value) else o_span(o_flat(value))


def o_contrast(value):
    """factor,numerator,denominator, read as "numerator versus denominator (factor factor)"."""
    if o_words(value) is not None and isinstance(value, str) and value.count(',') == 2:
        factor, numerator, denominator = value.split(',')
        if all(o_plain(part) for part in (factor, numerator, denominator)):
            return '%s versus %s (factor %s)' % (numerator, denominator, factor)
    return o_words(value)


def o_param_words(key, value):
    return o_contrast(value) if key == 'contrast' else o_words(value)


def o_dig(node, *keys):
    for key in keys:
        node = node.get(key, MISSING) if isinstance(node, dict) else MISSING
    return node


def o_pipeline(m, M):
    """References to the one Workflow/<name> versions entry other than Workflow/Nextflow of a nextflow
    wrapper (the wrapper kind first), or None."""
    if o_dig(m, 'predicate_facts', 'wrapper_kind') != 'nextflow':
        return None
    hits = []
    files = m.get('software_versions', MISSING)
    for i, entry in enumerate(files if isinstance(files, list) else []):
        versions = entry.get('versions', MISSING)
        if not isinstance(versions, dict):
            continue
        hits += [(i, j, key) for j, key in enumerate(sorted(versions))
                 if key != 'Workflow/Nextflow' and key.startswith('Workflow/')]
    if len(hits) != 1:
        return None
    i, j, key = hits[0]
    if o_words(key[9:]) is None or o_words(files[i]['versions'][key]) is None:
        return None
    return [M + '/predicate_facts/wrapper_kind', '%s/software_versions/%d/versions#%d.key' % (M, i, j),
            '%s/software_versions/%d/versions#%d.value' % (M, i, j)]


def o_subject(m):
    name = m.get('workflow_name', MISSING)
    if o_words(name) is not None:
        return o_words(name)
    return P_NO_NAME if o_absent(name) else P_HIDDEN_NAME


def o_prose_expected(rec):
    """The paragraph's sentences a set of records must produce, as (kind, references), in order."""
    out = []
    for k in range(1, rec.n + 1):
        m, M = rec.json['manifest%d' % k], 'manifest%d:' % k
        pipe = o_pipeline(m, M)
        refs = list(pipe) if pipe else [M + '/workflow_name'] + (
            [M + '/workflow_version'] if o_words(m.get('workflow_version', MISSING)) is not None else [])
        refs.append(M + '/predicate_facts/status')
        if pipe and o_words(m.get('workflow_name', MISSING)) is not None:
            refs.append(M + '/workflow_name')
        reference = m.get('reference', MISSING)
        if (o_dig(m, 'predicate_facts', 'wrapper_kind') == 'nextflow' and isinstance(reference, dict) and
                reference.get('comparison') == 'matched' and o_words(reference.get('build', MISSING)) is not None):
            if not pipe:
                refs.append(M + '/predicate_facts/wrapper_kind')
            refs += [M + '/reference/comparison', M + '/reference/build']
            if (o_words(reference.get('annotation_release', MISSING)) is not None and
                    isinstance(m.get('params'), dict) and 'gtf' in m['params']):
                refs += [M + '/params/gtf?', M + '/reference/annotation_release']
        params = m.get('params') if isinstance(m.get('params'), dict) else {}
        refs += [M + '/params/' + key for key in ('aligner', 'formula', 'contrast')
                 if o_param_words(key, params.get(key, MISSING)) is not None]
        complete = o_dig(m, 'predicate_facts', 'status') == 'COMPLETE'
        out.append(('prose-run' if complete else 'prose-configured', tuple(refs)))
    models = [rec.json['manifest%d' % k].get('agent_model', MISSING) for k in range(1, rec.n + 1)]
    if (rec.n >= 2 and all(isinstance(x, str) and x == models[0] for x in models) and models[0] != 'none'
            and o_words(models[0]) is not None):
        out.append(('prose-agent-all', tuple('manifest%d:/agent_model' % k for k in range(1, rec.n + 1))))
    else:
        for k, model in enumerate(models, 1):
            m, M = rec.json['manifest%d' % k], 'manifest%d:' % k
            pipe = o_pipeline(m, M)
            who = pipe[:2] if pipe else [M + '/workflow_name']
            if model == 'none':
                if o_absent(m.get('model_steps', MISSING)):
                    out.append(('prose-agent-none', tuple(who + [M + '/agent_model', M + '/model_steps'])))
            elif o_words(model) is not None:
                out.append(('prose-agent', tuple(who + [M + '/agent_model'])))
    if rec.plan:
        custom = re.search(r'/03_custom_analysis/[^/]*/PLAN\.md\Z', '/' + rec.approval.get('plan_path', '')) \
            if isinstance(rec.approval.get('plan_path'), str) else None
        # no dates in the paragraph: a UTC instant beside a local day could read as completion first
        out.append(('prose-approval', tuple(['approval:/plan_sha256'] + (['approval:/plan_path?'] if custom else []) +
                                            ['approval:/actor?'])))
        if rec.history:
            for e, entry in enumerate(rec.entries):
                if o_matches(entry, rec.approval):
                    H = 'history:#%d/' % e
                    refs = [H + 'stage', H + 'outcome']
                    if o_words(MISSING if entry['model'] is None else entry['model']) is not None:
                        refs.append(H + 'model')
                    out.append(('prose-history', tuple(refs)))
    out.append(('prose-closing', ()))
    return out


def o_who(refs, rec, M):
    """The name an agent sentence uses, from the references it cites first."""
    if refs[0] == M + '/predicate_facts/wrapper_kind':
        if o_resolve(rec, refs[0]) != 'nextflow':
            raise TraceError('a pipeline named for a wrapper that is not nextflow')
        return o_words(o_resolve(rec, refs[1])[9:]), refs[2:]
    if refs[0] != M + '/workflow_name':
        raise TraceError('an agent sentence names no workflow')
    return o_subject(rec.json[M[:-1]]), refs[1:]


def o_prose_line(kind, refs, rec):
    """A paragraph sentence rebuilt from the fields its Sources entry cites, read from the inputs."""
    if kind == 'prose-closing':
        if refs:
            raise TraceError('the closing sentence cites fields')
        return P_CLOSING
    if kind in ('prose-run', 'prose-configured'):
        k = {re.match(r'manifest(\d+):', ref).group(1) for ref in refs}
        if len(k) != 1:
            raise TraceError('%s cites more than one manifest' % kind)
        M = 'manifest%s:' % k.pop()
        m = rec.json[M[:-1]]
        tail = [ref[len(M):] for ref in refs]
        keys = [p for p in tail if '/versions#' in p and p.endswith('.key')]
        shown = {}
        for ref, path in zip(refs, tail):
            value = o_resolve(rec, ref)
            if path == '/workflow_name' and not keys:   # the subject: shown, or said missing
                continue
            if path == '/reference/comparison':
                if value != 'matched':
                    raise TraceError('the reference clause cites an unmatched registry check')
                continue
            if path == '/predicate_facts/wrapper_kind':
                if value != 'nextflow':
                    raise TraceError('a pipeline named for a wrapper that is not nextflow')
                continue
            if path == '/predicate_facts/status':
                if (value == 'COMPLETE') != (kind == 'prose-run'):
                    raise TraceError('%s does not fit the recorded status' % kind)
                shown[path] = value
                continue
            if path == '/params/gtf?':   # presence only: the run passed an annotation
                if not isinstance(m.get('params'), dict) or 'gtf' not in m['params']:
                    raise TraceError('an annotation release named for a run that passed no annotation')
                continue
            words = o_param_words(path.rsplit('/', 1)[-1], value) if path.startswith('/params/') else o_words(value)
            if words is None:
                raise TraceError('%s cites %s, which shows no words' % (kind, ref))
            shown[path] = (value, words)
        if keys:
            if '/predicate_facts/wrapper_kind' not in tail:
                raise TraceError('a pipeline named without its wrapper kind')
            name = o_resolve(rec, M + keys[0])
            if not name.startswith('Workflow/') or name == 'Workflow/Nextflow':
                raise TraceError('%s names a pipeline from %s' % (kind, name))
            values = [p for p in tail if p.endswith('.value')]
            if len(values) != 1 or values[0][:-6] != keys[0][:-4]:
                raise TraceError('%s cites a pipeline version that is not its name\'s' % kind)
            text = o_words(name[9:]) + ' ' + shown[values[0]][1]
        else:
            text = o_subject(m)
            if '/workflow_version' in shown:
                text += ' (workflow version %s)' % shown['/workflow_version'][1]
            if text.startswith((P_NO_NAME, P_HIDDEN_NAME)):
                text = text[0].upper() + text[1:]
        text += ' was run' if kind == 'prose-run' else ' was configured'
        if keys and '/workflow_name' in shown:
            text += ' through the GARS workflow ' + shown['/workflow_name'][1]
        if '/reference/build' in shown:
            if '/predicate_facts/wrapper_kind' not in tail:
                raise TraceError('a reference genome named for a step that is not an aligning pipeline')
            if '/reference/comparison' not in tail:
                raise TraceError('the reference clause does not cite the registry check')
            text += ' against the %s reference genome' % shown['/reference/build'][1]
            if '/reference/annotation_release' in shown:
                if '/params/gtf?' not in tail:
                    raise TraceError('an annotation release cited without the run\'s annotation')
                text += ' (annotation release %s)' % shown['/reference/annotation_release'][1]
        withs = [frame % shown['/params/' + key][1] for key, frame in
                 (('aligner', 'the %s aligner'), ('formula', 'the design formula %s'), ('contrast', 'the contrast %s'))
                 if '/params/' + key in shown]
        if len(withs) > 1:
            text += ' with ' + ', '.join(withs[:-1]) + ' and ' + withs[-1]
        elif withs:
            text += ' with ' + withs[0]
        if kind == 'prose-configured':
            status = shown['/predicate_facts/status']
            if o_words(status) is not None:
                text += '; its run status is ' + o_words(status)
            elif o_absent(status):
                text += '; its run status is ' + T_NOT
        return text + '.'
    if kind == 'prose-agent-all':
        models = [o_resolve(rec, ref) for ref in refs]
        if len(models) < 2 or len(set(json.dumps(x) for x in models)) != 1 or models[0] == 'none':
            raise TraceError('the agent models differ, or there is one workflow')
        return 'The agent model recorded for every workflow was %s.' % o_words(models[0])
    if kind in ('prose-agent', 'prose-agent-none'):
        M = re.match(r'manifest\d+:', refs[0]).group(0)
        who, rest = o_who(refs, rec, M)
        model = o_resolve(rec, rest[0])
        if kind == 'prose-agent-none':
            if model != 'none' or not o_absent(o_resolve(rec, rest[1])):
                raise TraceError('prose-agent-none for the agent model %r or beside model steps' % model)
            return 'The record for %s names no agent model.' % who
        return 'The agent model recorded for %s was %s.' % (who, o_words(model))
    if kind == 'prose-approval':
        if o_resolve(rec, 'approval:/plan_sha256') != hashlib.sha256(rec.raw['plan']).hexdigest():
            raise TraceError('the approval does not bind the plan')
        if 'approval:/plan_path?' in refs:
            path = o_resolve(rec, 'approval:/plan_path?')
            if not (isinstance(path, str) and re.search(r'(^|/)03_custom_analysis/[^/]*/PLAN\.md\Z', path)):
                raise TraceError('a custom analysis named for a plan outside stage 03')
            text = 'A separate custom analysis was planned, and its plan was approved'
        else:
            text = 'An analysis plan was approved'
        if any(r.startswith('approval:/') and r not in ('approval:/plan_sha256', 'approval:/plan_path?',
                                                         'approval:/actor?') for r in refs):
            raise TraceError('the approval sentence cites a field it may not state')
        actor = o_resolve(rec, 'approval:/actor?')
        return text + ' %s.' % (T_NOBY if o_absent(actor) else 'by the approver named in its approval record')
    if kind == 'prose-history':
        e = int(re.match(r'history:#(\d+)/', refs[0]).group(1))
        if not o_matches(rec.entries[e], rec.approval):
            raise TraceError('the history sentence cites another analysis')
        text = "The project's history records that custom analysis as complete"
        if 'history:#%d/date' % e in refs:
            raise TraceError('the history sentence states a date')
        if 'history:#%d/model' % e in refs:
            text += ', with the agent model ' + o_words(rec.entries[e]['model'])
        return text + '.'
    raise TraceError('unknown paragraph kind ' + kind)


def o_hides(rec, name):
    """A record whose sha256 would confirm a guessed withheld value: a manifest or approval record
    holding a path-like string anywhere (a storage URI included), an approval record naming an actor
    or a plan path at all, a history whose text holds a path-like value. The plan's hash is the
    approval's binding and stays published."""
    def pathy(texts):
        return any(PATH_LIKE.search(o_flat(t)) for t in texts)
    if name == 'plan':
        return False
    if name == 'history':
        return pathy([rec.raw['history'].decode('utf-8')])
    record = rec.approval if name == 'approval' else rec.json[name]
    if name == 'approval' and not (o_absent(record.get('actor', MISSING)) and o_absent(record.get('plan_path', MISSING))):
        return True
    return pathy(o_strings(record))


def o_line(kind, refs, rec):
    section, template, slots = KINDS[kind]
    if kind in ('record', 'record-unpublished'):
        name = refs[0].split(':')[0]
        label = {'plan': 'plan', 'approval': 'approval record', 'history': 'history'}.get(
            name, 'manifest ' + name[len('manifest'):])
        if (kind == 'record-unpublished') != o_hides(rec, name):
            raise TraceError('%s: the hash of %s is %s' % (kind, name, 'withheld wrongly' if kind ==
                                                            'record-unpublished' else 'an oracle for a withheld value'))
        if kind == 'record-unpublished':
            return template.format(label)
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
        elif slot == 'h':   # a hash of a file that names local paths: an oracle, never printed (0276)
            texts.append(T_NOT if o_absent(value) else 'not published, since the file names local paths')
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
        if not match or match.group(2) not in KINDS and match.group(2) not in PROSE:
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
        if section != (METHODS if kind in PROSE else KINDS[kind][0]):
            raise TraceError('line %d (%s) sits under %s' % (number, kind, section))
        want = o_prose_line(kind, refs, rec) if kind in PROSE else o_line(kind, refs, rec)
        if line != want:
            raise TraceError('line %d (%s) reads %r; its fields give %r' % (number, kind, line, want))
    return len(cited)


# ---- helpers ------------------------------------------------------------------------------------

def paragraph(text):
    """The journal paragraph's sentences: the lines between `# Methods` and `## Provenance`."""
    lines = text.split('\n')
    return lines[2:lines.index('## Provenance') - 1]


DE_RUN = ('rnaseq-de (workflow version v0.10.0) was run with the design formula `~ condition` and the contrast MT '
          'versus WT (factor condition).')
APPROVED = ('A separate custom analysis was planned, and its plan was approved by the approver '
            "named in its approval record.")
COMPLETED = ("The project's history records that custom analysis as complete, with the agent "
             "model claude-opus-5-5.")

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
        # The journal paragraph (0276): six sentences for two workflows, a plan and its history.
        self.assertEqual(paragraph(text), [
            'nfcore-rnaseq-wrapper (workflow version 3.26.0) was run against the fixture-build reference genome (annotation release '
            'fixture-release) with the star_salmon aligner.',
            DE_RUN, 'The agent model recorded for every workflow was claude-opus-5-5.', APPROVED, COMPLETED, P_CLOSING])
        for hidden in ('sha256', 'withheld', 'fixture-operator', 'fixture-workspace', '03_custom_analysis'):
            self.assertNotIn(hidden, '\n'.join(paragraph(text)))
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
        self.assertEqual(paragraph(text), [   # a prepare-only manifest: configured, never said to have run
            'rnaseq-de (workflow version v0.10.0) was configured with the design formula `~ condition` and the contrast MT versus WT '
            '(factor condition); its run status is not recorded.', P_CLOSING])
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
                                                        reason='reference_hash_mismatch',
                                                        observed={'fasta_sha256': '1' * 64, 'gtf_sha256': '2' * 64})),
            'an sha256 prompt hash': dict(m, model_steps=[dict(m['model_steps'][0],
                                                               prompt_sha256={'algorithm': 'sha256', 'value': 'e' * 64})]),
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
                if label == 'registry mismatch':   # the hash the run saw, not only the registry's (r3 F-2)
                    self.assertIn('Its reference registry check reads `mismatch`, reason '
                                  '`reference_hash_mismatch`; the run observed FASTA sha256 `%s` and GTF '
                                  'sha256 `%s`.' % ('1' * 64, '2' * 64), text)
                if label == 'an sha256 prompt hash':   # the hash kind is read, never assumed (r3 F-3)
                    self.assertIn('contract hash `%s` (algorithm `sha256`).' % ('e' * 64), text)
                if label == 'a string prompt hash':
                    self.assertIn('contract hash `%s` (algorithm not recorded).' % ('d' * 40), text)
        # The producers write sorted keys; a record whose file order is not sorted must still be
        # rendered, and cited, in sorted-key order.
        unsorted = copy.deepcopy(m)
        unsorted['params'] = dict(reversed(sorted(m['params'].items())))
        unsorted['software_versions'][0]['versions'] = {'z-tool': '2', 'a-tool': '1'}
        self.path('variant.json').write_text(json.dumps(unsorted, indent=2), encoding='utf-8')
        text = self.traced(('variant.json',))
        self.assertLess(text.index('parameter `aligner`'), text.index('parameter `outdir`'))
        self.assertLess(text.index('`a-tool`: `1`.'), text.index('`z-tool`: `2`.'))
        # A zero written with an exponent is a zero, not an underflow (r3 F-1's refusal stays narrow).
        zero = json.dumps(dict(m, params={'z': 'ZERO'})).replace('"ZERO"', '0.0e-400')
        self.path('variant.json').write_text(zero, encoding='utf-8')
        self.assertIn('parameter `z`: `0.0`.', self.traced(('variant.json',)))

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
        at = lines.index('### Parameters') - 1
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
        # (g) two workflows' model-step lines swapped, each still citing its own
        # field, so every line alone is right and only its place is wrong (review r1 F-3)
        def swap(a, b, kind):
            out = list(lines)
            out[a], out[b] = lines[b], lines[a]
            numbers = {'- line %d: %s:' % (a + 1, kind): '- line %d: %s:' % (b + 1, kind),
                       '- line %d: %s:' % (b + 1, kind): '- line %d: %s:' % (a + 1, kind)}
            out = [next((l.replace(o, n) for o, n in numbers.items() if l.startswith(o)), l) for l in out]
            self.assertEqual(sum(1 for x, y in zip(out, lines) if x != y), 4)   # two lines, two citations
            return '\n'.join(out)

        a, b = [i for i, l in enumerate(lines) if l.startswith('It records a model-mediated step: ')]
        with self.assertRaises(TraceError):   # (the configuration lines now read alike: their hashes are withheld)
            verify(swap(a, b, 'model-step'), rec)
        # ... and a tool version moved under the other workflow's versions file
        a = lines.index('  - `FIXTURE_PROCESS/fixture-tool`: `1.0.0`.')
        b = lines.index('  - `pandas`: `fixture-1`.')
        with self.assertRaises(TraceError):
            verify(swap(a, b, 'version'), rec)
        # (h) the journal paragraph (0276): a value changed, a clause invented for a missing field,
        # "configured" turned into "run" with no status, a date or a person added, a sentence cited
        # from another manifest, the approver named, a dropped clause's field still cited
        for old, new, text, records in (
                ('with the star_salmon aligner.', 'with the hisat2 aligner.', complete, rec),
                ('was configured with', 'was configured against the GRCh38 reference genome with', sparse, sparse_rec),
                ('was configured with the design formula `~ condition` and the contrast MT versus WT (factor '
                 'condition); its run status is not recorded.', 'was run with the design formula `~ condition` and '
                 'the contrast MT versus WT (factor condition).', sparse, sparse_rec),
                ('rnaseq-de (workflow version v0.10.0) was configured', 'rnaseq-de (workflow version v0.10.0) was run', sparse, sparse_rec),
                ('the contrast MT versus WT', 'the contrast WT versus MT', complete, rec),
                ('by the approver named in its approval record.', 'by fixture-operator.', complete, rec),
                ('by the approver named in its approval record.', 'by the approver the run recorded.', complete, rec),
                ('records that custom analysis as complete,',
                 'records that custom analysis as complete on 29 September 2026,', complete, rec),
                ('its plan was approved by', 'its plan was approved on 29 September 2026 by', complete, rec),
                ('A separate custom analysis was planned, and its plan', 'The workflows\' plan', complete, rec),
                ('The agent model recorded for every workflow was claude-opus-5-5.',
                 'Every workflow records the agent model claude-opus-5-6.', complete, rec),
                ("every value traces to the run's records (Provenance).",
                 "every value traces to the run's records (Provenance), and the plan was executed as approved.",
                 complete, rec),
                ('prose-run: `manifest1:/workflow_name', 'prose-run: `manifest2:/workflow_name', complete, rec),
                ('manifest1:/params/aligner`', 'manifest1:/params/aligner manifest1:/params/fasta`', complete, rec),
                ('prose-approval: `approval:/plan_sha256 approval:/plan_path? approval:/actor?`',
                 'prose-approval: `approval:/plan_sha256 approval:/plan_path? approval:/timestamp approval:/actor?`',
                 complete, rec)):
            with self.subTest(paragraph=new):
                with self.assertRaises(TraceError):
                    verify(plant(old, new, text), records)
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

        def filling(subject):   # the paragraph fills a dropped clause with a plausible value
            original = subject.words
            return lambda value: original(value) or 'GRCh38'
        filled = self.in_process(argv, [('words', filling)])
        self.assertIn('with the GRCh38 aligner', filled)
        with self.assertRaises(TraceError):
            verify(filled, sparse_rec)
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
                text = self.traced(('local-manifest.json',))
                self.assertIn('was approved at not recorded by the approver the run recorded.', text)
                self.assertIn('A separate custom analysis was planned, and its plan was approved by the approver '
                              "named in its approval record.", paragraph(text))
        self.dump('approval.json', approval)
        self.paragraph_drops_clauses()

    def paragraph_drops_clauses(self):
        """Each journal-paragraph clause whose field is missing, empty or path-like is dropped,
        never filled; every case is also traced by the oracle (0276)."""
        de = self.load('local-manifest.json')
        nf = self.load('nfcore-manifest.json')
        reference = ' against the fixture-build reference genome (annotation release fixture-release)'
        design = ' with the design formula `~ condition` and the contrast MT versus WT (factor condition)'

        def edit(base, *changes):
            m = copy.deepcopy(base)
            for path, value in changes:
                target = m
                for key in path[:-1]:
                    target = target[key]
                if value == 'delete':
                    del target[path[-1]]
                else:
                    target[path[-1]] = value
            return m

        agent = 'The agent model recorded for rnaseq-de was claude-opus-5-5.'
        cases = [
            ('name missing', edit(de, (('workflow_name',), 'delete')),
             ['A workflow whose name is not recorded (workflow version v0.10.0) was run' + design + '.',
              'The agent model recorded for a workflow whose name is not recorded was claude-opus-5-5.']),
            ('name path-like', edit(de, (('workflow_name',), '/abs/name')),
             ['A workflow whose recorded name is withheld (workflow version v0.10.0) was run' + design + '.',
              'The agent model recorded for a workflow whose recorded name is withheld was claude-opus-5-5.']),
            ('version missing', edit(de, (('workflow_version',), '')), ['rnaseq-de was run' + design + '.', agent]),
            ('status missing', edit(de, (('predicate_facts', 'status'), 'delete')),
             ['rnaseq-de (workflow version v0.10.0) was configured' + design + '; its run status is not recorded.', agent]),
            ('status failed', edit(de, (('predicate_facts', 'status'), 'FAILED')),
             ['rnaseq-de (workflow version v0.10.0) was configured' + design + '; its run status is FAILED.', agent]),
            ('status path-like', edit(de, (('predicate_facts', 'status'), '/abs/status')),
             ['rnaseq-de (workflow version v0.10.0) was configured' + design + '.', agent]),
            ('predicate facts missing', edit(de, (('predicate_facts',), 'delete')),
             ['rnaseq-de (workflow version v0.10.0) was configured' + design + '; its run status is not recorded.', agent]),
            ('reference missing', edit(de, (('reference',), 'delete')), ['rnaseq-de (workflow version v0.10.0) was run' + design + '.', agent]),
            ('registry mismatch', edit(de, (('reference', 'comparison'), 'mismatch')),
             ['rnaseq-de (workflow version v0.10.0) was run' + design + '.', agent]),
            ('registry check missing', edit(de, (('reference', 'comparison'), 'delete')),
             ['rnaseq-de (workflow version v0.10.0) was run' + design + '.', agent]),
            ('build missing', edit(de, (('reference', 'build'), None)), ['rnaseq-de (workflow version v0.10.0) was run' + design + '.', agent]),
            ('release missing', edit(de, (('reference', 'annotation_release'), '  ')),
             ['rnaseq-de (workflow version v0.10.0) was run' + design + '.', agent]),
            ('formula missing', edit(de, (('params', 'formula'), 'delete')),
             ['rnaseq-de (workflow version v0.10.0) was run' + ' with the contrast MT versus WT (factor condition).', agent]),
            ('formula path-like', edit(de, (('params', 'formula'), '~ /abs/batch')),
             ['rnaseq-de (workflow version v0.10.0) was run' + ' with the contrast MT versus WT (factor condition).', agent]),
            ('contrast missing', edit(de, (('params', 'contrast'), [])),
             ['rnaseq-de (workflow version v0.10.0) was run' + ' with the design formula `~ condition`.', agent]),
            ('contrast of two parts', edit(de, (('params', 'contrast'), 'condition,MT')),
             ['rnaseq-de (workflow version v0.10.0) was run' + ' with the design formula `~ condition` and the contrast '
              '`condition,MT`.', agent]),
            ('params missing', edit(de, (('params',), 'delete')), ['rnaseq-de (workflow version v0.10.0) was run' + '.', agent]),
            ('agent model missing', edit(de, (('agent_model',), 'delete')), ['rnaseq-de (workflow version v0.10.0) was run' + design + '.']),
            ('agent model none', edit(de, (('agent_model',), 'none'), (('model_steps',), [])),
             ['rnaseq-de (workflow version v0.10.0) was run' + design + '.', 'The record for rnaseq-de names no agent model.']),
            ('aligner missing', edit(nf, (('params', 'aligner'), 'delete')),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + '.',
              'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ('aligner not plain', edit(nf, (('params', 'aligner'), 'star*salmon')),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + ' with the `star*salmon` aligner.',
              'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ('every with clause', edit(nf, (('params', 'formula'), '~ batch + condition'),
                                       (('params', 'contrast'), 'condition,MT,WT')),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + ' with the star_salmon aligner, the design '
              'formula `~ batch + condition` and the contrast MT versus WT (factor condition).',
              'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ("the pipeline's own name", edit(nf, (('software_versions', 0, 'versions'), {
                'FIXTURE_PROCESS/fixture-tool': '1.0.0', 'Workflow/Nextflow': '24.10.5', 'Workflow/nf-core/rnaseq': 'v3.26.0'})),
             ['nf-core/rnaseq v3.26.0 was run through the GARS workflow nfcore-rnaseq-wrapper' + reference +
              ' with the star_salmon aligner.', 'The agent model recorded for nf-core/rnaseq was claude-opus-5-5.']),
            ('two pipeline names', edit(nf, (('software_versions', 0, 'versions'), {
                'Workflow/nf-core/rnaseq': 'v3.26.0', 'Workflow/nf-core/other': '1.0'})),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + ' with the star_salmon aligner.',
              'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ('pipeline version missing', edit(nf, (('software_versions', 0, 'versions'), {'Workflow/nf-core/rnaseq': ''})),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + ' with the star_salmon aligner.',
              'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ('pipeline with no wrapper name', edit(nf, (('workflow_name',), None), (('software_versions', 0, 'versions'), {
                'Workflow/nf-core/rnaseq': 'v3.26.0'})),
             ['nf-core/rnaseq v3.26.0 was run' + reference + ' with the star_salmon aligner.',
              'The agent model recorded for nf-core/rnaseq was claude-opus-5-5.']),
            # review r1 F-2: a path-like value driven into each clause on its own
            ('release path-like', edit(de, (('reference', 'annotation_release'), '/abs/gencode.v44.gtf')),
             ['rnaseq-de (workflow version v0.10.0) was run' + design + '.', agent]),
            ('pipeline name path-like', edit(nf, (('software_versions', 0, 'versions'), {'Workflow//abs/pipeline': 'v1'})),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + ' with the star_salmon aligner.',
              'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ('pipeline version path-like', edit(nf, (('software_versions', 0, 'versions'), {'Workflow/nf-core/rnaseq': '/abs/v1'})),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + ' with the star_salmon aligner.',
              'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ('pipeline version a bucket', edit(nf, (('software_versions', 0, 'versions'), {
                'Workflow/nf-core/rnaseq': 's3://runs-123456789012/v1'})),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + ' with the star_salmon aligner.',
              'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ('wrapper name path-like with a pipeline', edit(nf, (('workflow_name',), '/abs/wrapper'), (
                ('software_versions', 0, 'versions'), {'Workflow/nf-core/rnaseq': 'v3.26.0'})),
             ['nf-core/rnaseq v3.26.0 was run' + reference + ' with the star_salmon aligner.',
              'The agent model recorded for nf-core/rnaseq was claude-opus-5-5.']),
            # review r1 F-11: only a nextflow wrapper's versions name a pipeline
            ('a pipeline entry in a local wrapper', edit(de, (('software_versions', 0, 'versions'), {
                'Workflow/lab/de-script': '0.1', 'python': '3.9.0'})),
             [DE_RUN, agent]),
            # review r1 F-3: a three-part contrast is read in parts only when every part is plain
            ('contrast with Markdown in a part', edit(de, (('params', 'contrast'), 'condition,*MT*,[WT](http://x)')),
             ['rnaseq-de (workflow version v0.10.0) was run' + ' with the design formula `~ condition` and '
              'the contrast `condition,*MT*,[WT](http://x)`.', agent]),
            ('contrast with spaces', edit(de, (('params', 'contrast'), 'condition, MT, WT')),
             ['rnaseq-de (workflow version v0.10.0) was run' + ' with the design formula `~ condition` and '
              'the contrast `condition, MT, WT`.', agent]),
            ('contrast part starting www.', edit(de, (('params', 'contrast'), 'condition,www.x.com,WT')),
             ['rnaseq-de (workflow version v0.10.0) was run' + ' with the design formula `~ condition` and '
              'the contrast `condition,www.x.com,WT`.', agent]),
            # review r1 F-9 and F-12: a GitHub autolink and a non-string value stay in code spans
            ('aligner starting www.', edit(nf, (('params', 'aligner'), 'WWW.example.com')),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + ' with the `WWW.example.com` aligner.',
              'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ('numbers and booleans', edit(de, (('params', 'formula'), True), (('params', 'contrast'), 3)),
             ['rnaseq-de (workflow version v0.10.0) was run' + ' with the design formula `true` and the '
              'contrast `3`.', agent]),
            # review r1 F-13: `none` beside a recorded model step is a contradiction, stated in Provenance only
            ('agent model none beside a model step', edit(de, (('agent_model',), 'none')),
             ['rnaseq-de (workflow version v0.10.0) was run' + design + '.']),
            # review r3 F-2: an annotation release only for a run that passed an annotation (methylseq: FASTA only)
            ('no annotation passed', edit(nf, (('params', 'gtf'), 'delete')),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run against the fixture-build reference genome with '
              'the star_salmon aligner.', 'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            # review r3 F-3: a list or dict value is flattened like a string
            ('a list formula with a separator', edit(de, (('params', 'formula'), ['~ condition\u2028## invented'])),
             ['rnaseq-de (workflow version v0.10.0) was run with the design formula `["~ condition ## invented"]` and the '
              'contrast MT versus WT (factor condition).', agent]),
            ('a dict aligner with NEL', edit(nf, (('params', 'aligner'), {'a': 'star\x85salmon'})),
             ['nfcore-rnaseq-wrapper (workflow version 3.26.0) was run' + reference + ' with the `{"a":"star salmon"}` '
              'aligner.', 'The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.']),
            ('a list agent model with RLO', edit(de, (('agent_model',), ['opus\u202eevil'])),
             [DE_RUN, 'The agent model recorded for rnaseq-de was `["opus evil"]`.']),
        ]
        for label, manifest, expected in cases:
            with self.subTest(clause=label):
                self.dump('variant.json', manifest)
                text = self.traced(('variant.json',))
                self.assertEqual(paragraph(text), expected + [APPROVED, COMPLETED, P_CLOSING])
        # Two workflows with different agent models each get their own sentence.
        self.dump('variant.json', dict(de, agent_model='other-model'))
        sentences = paragraph(self.traced(('nfcore-manifest.json', 'variant.json'), stage03=False))
        self.assertEqual(sentences[2:], ['The agent model recorded for nfcore-rnaseq-wrapper was claude-opus-5-5.',
                                         'The agent model recorded for rnaseq-de was other-model.', P_CLOSING])
        self.dump('variant.json', dict(de, agent_model='none', model_steps=[]))   # `none` is never an agent model
        self.dump('variant2.json', dict(nf, agent_model='none', model_steps=[]))
        sentences = paragraph(self.traced(('variant2.json', 'variant.json'), stage03=False))
        self.assertEqual(sentences[2:], ['The record for nfcore-rnaseq-wrapper names no agent model.',
                                         'The record for rnaseq-de names no agent model.', P_CLOSING])
        for shared in ('/abs/agent', 's3://runs-123456789012/agent'):   # review r1 F-2: a shared path-like model
            self.dump('variant.json', dict(de, agent_model=shared))
            self.dump('variant2.json', dict(nf, agent_model=shared))
            sentences = paragraph(self.traced(('variant2.json', 'variant.json'), stage03=False))
            self.assertEqual(len(sentences), 3, sentences)
            self.assertNotIn('agent model', '\n'.join(sentences))
        self.dump('variant.json', dict(de, agent_model=1))   # review r2 F-7: only identical strings fold
        self.dump('variant2.json', dict(nf, agent_model=True))
        sentences = paragraph(self.traced(('variant2.json', 'variant.json'), stage03=False))
        self.assertEqual(sentences[2:4], ['The agent model recorded for nfcore-rnaseq-wrapper was `true`.',
                                          'The agent model recorded for rnaseq-de was `1`.'])
        self.dump('variant.json', dict(de, agent_model=None))   # ... and an absent one is never folded in
        self.assertNotIn('Every workflow', '\n'.join(paragraph(self.traced(('nfcore-manifest.json', 'variant.json')))))
        # The approval and the history drop their clauses the same way.
        approval = self.load('approval.json')
        self.dump('approval.json', dict(approval, actor=''))
        self.assertIn('A separate custom analysis was planned, and its plan was approved with no '
                      "approver named in its approval record.",
                      paragraph(self.traced(('local-manifest.json',))))
        self.dump('approval.json', approval)
        history = self.path('HISTORY.md').read_text(encoding='utf-8')
        for label, changed, sentence in (
                ('no model line', history.replace('Model: claude-opus-5-5\nPlan:', 'Plan:'),
                 "The project's history records that custom analysis as complete."),
                ('a model that is not plain', history.replace('Model: claude-opus-5-5\nPlan:', 'Model: opus *5*\nPlan:'),
                 "The project's history records that custom analysis as complete, with the agent "
                 "model `opus *5*`."),
                ('not recorded', HEADER, None),
                # review r1 F-5 and F-2: a history date that is not a real date, or is path-like, is dropped
                ('an unfilled date', history.replace('## 2026-09-29 \u2014 03_custom', '## <ISO-8601 date> \u2014 03_custom'),
                 "The project's history records that custom analysis as complete, with the agent model claude-opus-5-5."),
                ('a date without zero padding', history.replace('## 2026-09-29 \u2014 03_custom', '## 2026-9-29 \u2014 03_custom'),
                 "The project's history records that custom analysis as complete, with the agent model claude-opus-5-5."),
                ('an impossible date', history.replace('## 2026-09-29 \u2014 03_custom', '## 2026-02-30 \u2014 03_custom'),
                 "The project's history records that custom analysis as complete, with the agent model claude-opus-5-5."),
                ('a path-like date', history.replace('## 2026-09-29 \u2014 03_custom', '## /abs/run-2026-09-29 \u2014 03_custom'),
                 "The project's history records that custom analysis as complete, with the agent model claude-opus-5-5."),
                ('a path-like model', history.replace('Model: claude-opus-5-5\nPlan:', 'Model: s3://runs-123456789012/m\nPlan:'),
                 "The project's history records that custom analysis as complete.")):
            with self.subTest(history=label):
                self.path('HISTORY.md').write_text(changed, encoding='utf-8')
                sentences = paragraph(self.traced(('local-manifest.json',)))
                if sentence is None:
                    self.assertEqual(sentences, [DE_RUN, agent, APPROVED, P_CLOSING])
                else:
                    self.assertEqual(sentences, [DE_RUN, agent, APPROVED, sentence, P_CLOSING])
        # review r3 F-1: approved at 01:30Z on 30 September (21:30 the evening before in New York), completed
        # on the local 29 September: the paragraph states no date, so it can never read completion first
        late = dict(approval, timestamp='2026-09-30T01:30:00Z')
        self.dump('approval.json', late)
        self.path('HISTORY.md').write_text(history, encoding='utf-8')
        sentences = paragraph(self.traced(('local-manifest.json',)))
        self.assertEqual(sentences, [DE_RUN, agent, APPROVED, COMPLETED, P_CLOSING])
        self.assertNotIn('September', '\n'.join(sentences))
        self.dump('approval.json', approval)
        self.path('HISTORY.md').write_text(history, encoding='utf-8')

    def test_local_paths_are_never_printed(self):
        complete = self.traced()
        self.assertNotIn('/fixture-workspace', complete)
        self.assertIn('parameter `aligner`: `star_salmon`.', complete)
        m = self.load('local-manifest.json')
        hostile = ['/abs/secret', '~/home-secret', '~someone/secret', '\\\\server\\share', 'C:\\data\\x',
                   'd:/data/x', 'file:///etc/x', 'FILE:x', '--outdir=/abs/secret', 'a /abs/secret',
                   '"/quoted/abs"', '{"nested": "/abs/secret"}', 'x;/abs', '(/abs)', 'line\n/abs',
                   'user@host:/abs/secret', 'cat x >/abs/secret', 'a|/abs/secret', 'key:/abs/secret',
                   'x&/abs/secret', 'a+/abs/secret', 'tab\t/abs/secret', 'https:///etc/secret',
                   'sftp:///abs/secret', '\u212a/abs/secret', 'user@host:~jdoe/secret', 'host:~/secret',
                   'x:C:\\secret\\abs',
                   # storage URIs (the coordinator's reproduced leak, 5 Oct): a runs bucket names the account
                   's3://secret-runs-123456789012/work', 'S3://secret-runs-123456789012',
                   'nextflow run nf-core/rnaseq -work-dir s3://secret-runs-123456789012/work -resume',
                   '-work-dir=s3://secret-runs-123456789012/work', 's3a://secret-b/x', 's3n://secret-b/x',
                   'gs://secret-bucket/x', 'gcs://secret-bucket/x', 'az://secret-container/x',
                   'abfss://secret@acct.dfs.core.windows.net/x', 'wasbs://secret@acct/x', 'file://secret-host/x',
                   '(s3://secret-b/x)', '"s3://secret-b/x"']
        for value in hostile:
            with self.subTest(value=value):
                changed = dict(m, params={'p': value, value: 'key-side', 'nested': {'deep': [value]},
                                          'aligner': value, 'formula': value, 'contrast': 'c,' + value + ',WT'},
                               reference=dict(m['reference'], build=value),
                               containers=[{'process': 'P', 'image': value, 'image_sha256': 'f' * 64}],
                               command={'path': value, 'sha256': 'c' * 64},
                               workflow_version=[value])
                self.dump('variant.json', changed)
                text = self.traced(('variant.json',), stage03=False)
                self.assertNotIn(value, text)
                self.assertNotIn('secret', text)
                self.assertNotIn('/abs', text)
                self.assertNotIn('123456789012', text)
                self.assertIn('parameter `p`: a path-like value, withheld.', text)
                self.assertIn('parameter `nested`: a path-like value, withheld.', text)
                self.assertIn('parameter a path-like value, withheld: `key-side`.', text)
                self.assertEqual(paragraph(text)[0], 'rnaseq-de was run.')   # every clause dropped (0276)
        for value in ('~ condition', 'condition,MT,WT', 'quay.io/biocontainers/fastqc:0.12.1',
                      'https://depot.galaxyproject.org/singularity/fastqc', 'pipeline_info/fixture.sif',
                      'N/A', 'sha256:' + 'a' * 64, 'quay.io:443/biocontainers/fastqc', 'my-s3://x', 'https://s3.amazonaws.com',
                      './relative/x', '../relative/x', '$HOME/x', 'a\\b', 'fixture/tool@sha256:' + 'b' * 64,
                      '\u212a:\\x', 'zero 0e-400', 'f\u0130le:x', 'pattern:\\d+'):
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
        # A record's sha256 is an offline oracle for any value the page does not print (0276, relayed by
        # the Row-orchestrator from the reproduction-plan review): never published for such a record.
        for name in ('approval.json', 'local-manifest.json', 'HISTORY.md'):
            digest = hashlib.sha256(self.path(name).read_bytes()).hexdigest()
            self.assertNotIn(digest, text, name)
        self.assertIn('- approval record: sha256 not published, since the record holds values this page does not '
                      'print.', text)
        self.assertIn('- plan: sha256 `%s`.' % approval['plan_sha256'], text)   # the binding stays published
        # review r2 F-1: commands.sh and the assay config are templated files holding the home path, so
        # their recorded hashes are oracles too; neither is printed, for any manifest
        for name in ('nfcore-manifest.json', 'local-manifest.json'):
            m = self.load(name)
            page = self.traced((name,))
            for digest in (m['command']['sha256'], m['config_sha256']):
                self.assertNotIn(digest, page, name)
            self.assertIn('Its configuration sha256 is not published, since the file names local paths.', page)
            self.assertIn('Its exact submission: `reproducibility/commands.sh`, sha256 not published, since the file '
                          'names local paths.', page)
        for changed, published in ((dict(approval, actor=None, plan_path=None), True),
                                   (dict(approval, actor=None), False), (dict(approval, plan_path=''), False),
                                   (dict(approval, actor=None, plan_path='projects/rna-test/03_custom_analysis/'
                                                                          '01_fixture-followup/PLAN.md'), False),
                                   (dict(approval, actor=None, plan_path=None, expiry='/abs/x'), False)):
            with self.subTest(approval_hash=changed):
                self.dump('approval.json', changed)
                text = self.traced(('local-manifest.json',))
                digest = hashlib.sha256(self.path('approval.json').read_bytes()).hexdigest()
                self.assertEqual(digest in text, published)
        m = self.load('local-manifest.json')   # a manifest with nothing withheld keeps its hash
        clean = {key: value for key, value in m.items() if not PATH_LIKE.search(json.dumps(value))}
        clean['params'] = {'formula': '~ condition', 'contrast': 'condition,MT,WT'}
        self.dump('variant.json', clean)
        self.assertIn(hashlib.sha256(self.path('variant.json').read_bytes()).hexdigest(),
                      self.traced(('variant.json',), stage03=False))
        for bucket in ('s3://runs-123456789012/work', 'nextflow run x -work-dir s3://runs-123456789012/w'):
            with self.subTest(hidden_in=bucket):   # a bucket only in a field the page never prints
                self.dump('variant.json', dict(clean, unprinted_field=bucket))
                text = self.traced(('variant.json',), stage03=False)
                self.assertNotIn(hashlib.sha256(self.path('variant.json').read_bytes()).hexdigest(), text)
                self.assertIn('- manifest 1: sha256 not published', text)

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
                lines = [l for l in rendered.split('\n') if l.startswith("The project's history records `")]
                prose = [l for l in rendered.split('\n')
                         if l.startswith("The project's history records that custom analysis")]
                self.assertEqual(len(prose), len(lines))   # one paragraph sentence per matched entry
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
                changed = dict(m, workflow_name=value, params={value: value, 'aligner': value, 'formula': value,
                                                               'contrast': value},
                               reference=dict(m['reference'], build=value, annotation_release=value),
                               software_versions=[{'path': value, 'sha256': value, 'versions': {value: value}}],
                               containers=[{'process': value, 'image': value}], agent_model=value)
                self.dump('variant.json', changed)
                # A text file cannot hold a lone surrogate or break a line inside one entry field.
                model = value.replace('\n', ' ').replace('\r', ' ').replace('\ud800', '?')
                history.write_text(saved.replace('Model: claude-opus-5-5\nPlan:', 'Model: ' + model + '\nPlan:'),
                                   encoding='utf-8')
                text = self.traced(('variant.json',))
                self.assertEqual([l for l in text.split('\n') if l.startswith('#')], list(HEADINGS))
                for sentence in paragraph(text):   # one physical line per sentence (0276)
                    self.assertTrue(sentence.endswith('.') and (sentence[:1].isupper() or sentence[:1] == '`'), sentence)
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
                                (b'{"params": {"x": 1e-400}}', 'manifest 1 holds a number that rounds to zero'),
                                (b'{"params": {"x": [-1E-999]}}', 'manifest 1 holds a number that rounds to zero'),
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
            target = Path(argv[index])
            linked = self.root / ('linked-' + target.name)
            os.link(str(target), str(linked))
            # The same file spelled apart: a dot segment, a hard link, and a case variant, which on a
            # case-insensitive filesystem (the macOS default) names the input itself (review r2 F-1).
            spellings = [self.inputs / '.' / target.name, linked]
            upper = target.with_name(target.name.upper())
            if upper.exists():
                spellings.append(upper)
            for spelling in spellings:
                with self.subTest(overwrite=role, spelling=spelling.name):
                    before = target.read_bytes()
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        self.assertEqual(renderer.main(argv[:-1] + [str(spelling)]), 1)
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
