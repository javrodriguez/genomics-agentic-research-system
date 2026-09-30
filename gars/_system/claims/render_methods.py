#!/usr/bin/env python3
"""Render a Methods paragraph from a run's own records; Python 3.6, standard library only.

  python3 _system/claims/render_methods.py --manifest <reproducibility/manifest.json> [--manifest ...]
      [--plan <PLAN.md> --approval <approval record> [--history <HISTORY.md>]] --out <methods.md>

Every line is fixed words plus values read from the named records, and the Sources section lists,
for every line, the record fields its values came from (decision 0236). A missing or empty field
reads "not recorded"; a value holding a local path is withheld; nothing is guessed, no model and no
network is involved, and no file other than the named ones is opened. The approval line needs an
approval record whose plan_sha256 is the plan's sha256, and it names "the approver the run
recorded", never the record's actor. Exit 0 written; 1 refused, with the reason on stderr and any
earlier output left as it was; 2 usage.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

NOT_RECORDED = 'not recorded'
WITHHELD = 'a path-like value, withheld'
BY_APPROVER = 'by the approver the run recorded'
NO_APPROVER = 'with no approver named in its approval record'
# Where an absolute path can begin (/x, \x, ~/x, ~user/x, C:\x, C:/x); every position is tried.
PATH_START = re.compile(r'''(?=(/|\\|~[^\s/"']*/|[A-Za-z]:[\\/]))''')
# A path start preceded by one of these is part of a relative path, a word or a URL (a/b, ./b, a\b).
IN_WORD = frozenset('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._~/:\\-')
FILE_SCHEME = re.compile(r'(?<![A-Za-z0-9])[Ff][Ii][Ll][Ee]:')   # ASCII only, no re.I folding
FLATTENED = ('Cc', 'Cf', 'Cs', 'Zl', 'Zp')  # control, format, surrogate, line and paragraph separators
DIGEST = re.compile(r'[0-9a-f]{64}\Z')
UTC = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z')
ENTRY = re.compile('## (.+?) \u2014 (.+?) \u2014 (.+?)\\s*\\Z')

PARAGRAPH, PARAMETERS, SOFTWARE, CITATION, RECORDS, SOURCES = (
    '# Methods', '## Parameters', '## Software used', '## Citation', '## Records read', '## Sources')
# The closed vocabulary: each kind of line, its section and its fixed words ({} is one slot).
KINDS = {
    'workflow': (PARAGRAPH, 'The run manifest of workflow {} records: version {}; pipeline commit {}; '
                            'GARS wrapper {}; GARS commit {}; template version {}; status {}.'),
    'failure': (PARAGRAPH, 'Its failure class is {}.'),
    'reference': (PARAGRAPH, 'Its reference genome: build {}; annotation release {}; '
                             'FASTA sha256 {}; GTF sha256 {}.'),
    'reference-check': (PARAGRAPH, 'Its reference registry check reads {}, reason {}; the run '
                                   'observed FASTA sha256 {} and GTF sha256 {}.'),
    'reference-absent': (PARAGRAPH, 'Its reference genome is not recorded.'),
    'config': (PARAGRAPH, 'Its configuration sha256 is {}.'),
    'threads': (PARAGRAPH, 'Its thread count is {}.'),
    'command': (PARAGRAPH, 'Its exact submission: {}, sha256 {}.'),
    'command-absent': (PARAGRAPH, 'Its exact submission is not recorded.'),
    'agent': (PARAGRAPH, 'Its agent model is {}.'),
    'model-step': (PARAGRAPH, 'It records a model-mediated step: model {}; provider {}; '
                              'contract {}; contract hash {} (algorithm {}).'),
    'model-steps-absent': (PARAGRAPH, 'Its model-mediated steps are not recorded.'),
    'approval': (PARAGRAPH, 'The analysis plan with sha256 {} was approved at {} {}.'),
    'history': (PARAGRAPH, "The project's history records {} as {} on {}, with model {} and template "
                           "version {}."),
    'history-absent': (PARAGRAPH, "The approved analysis's completion is not recorded in the "
                                  "project's history."),
    'pointer': (PARAGRAPH, "Each workflow's parameters, random seeds, software versions and "
                           "container images are listed below."),
    'param': (PARAMETERS, '- {} parameter {}: {}.'),
    'params-absent': (PARAMETERS, '- {}: parameters are not recorded.'),
    'seed': (PARAMETERS, '- {} random seed for {}: {}.'),
    'seed-unset': (PARAMETERS, '- {} random seed for {}: not recorded; seed supported {}, '
                               'determinism {}.'),
    'seeds-text': (PARAMETERS, '- {} random seeds: {}.'),
    'seeds-absent': (PARAMETERS, '- {}: random seeds are not recorded.'),
    'gars': (SOFTWARE, '- GARS commit {}, template version {} (workflow {}).'),
    'workflow-version': (SOFTWARE, '- Workflow {} version {}, pipeline commit {}.'),
    'versions-file': (SOFTWARE, '- {} software versions (file {}, sha256 {}):'),
    'version': (SOFTWARE, '  - {}: {}.'),
    'version-absent': (SOFTWARE, '  - versions not recorded.'),
    'versions-absent': (SOFTWARE, '- {}: software versions are not recorded.'),
    'container': (SOFTWARE, '- {} container for process {}: image {}, digest {}, image file '
                            'sha256 {}.'),
    'containers-absent': (SOFTWARE, '- {}: container images are not recorded.'),
    'citation': (CITATION, "Cite GARS at commit {}; the GARS repository's CITATION.cff file gives "
                           "the preferred citation."),
    'citation-absent': (CITATION, 'The GARS commit to cite is not recorded for workflow {}.'),
    'record': (RECORDS, '- {}: sha256 {}.'),
}
MISSING = object()


class Refusal(Exception):
    """An input the renderer will not state anything from."""


def flatten(text):
    """One physical line: every control, format or separator character shown as a space."""
    return ''.join(' ' if unicodedata.category(c) in FLATTENED else c for c in text)


def absent(value):
    """Missing, null, [], {} or text with nothing but whitespace, control or format characters."""
    if value is MISSING or value is None or value == [] or value == {}:
        return True
    return isinstance(value, str) and not flatten(value).strip()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            for text in strings(item):
                yield text
    elif isinstance(value, list):
        for item in value:
            for text in strings(item):
                yield text


def path_like(text):
    """True when `text` holds an absolute path, which names a machine, not a method: a path start
    with nothing, or anything but a letter, digit or one of . _ ~ / : \\ - before it; right after a
    colon, a single slash (host:/x, not https://x), three (a URL with no host, https:///x), ~/ or
    ~user/ (user@host:~user/x) or a drive letter (x:C:\\x), but not a lone backslash; or a file:
    scheme."""
    if FILE_SCHEME.search(text):
        return True
    for start in PATH_START.finditer(text):
        at = start.start()
        before = text[at - 1] if at else None
        if before is None or before not in IN_WORD:
            return True
        if before == ':' and text[at] == '/' and (text[at + 1:at + 2] != '/' or text[at:at + 3] == '///'):
            return True
        if before == ':' and text[at] != '/' and text[at] != '\\':   # host:~user/x, x:C:\x
            return True
    return False


def span(text):
    """A CommonMark code span that shows `text` exactly: no record text can close it early."""
    runs = [len(run) for run in re.findall('`+', text)]
    fence = '`' * ((max(runs) if runs else 0) + 1)
    if text[:1] == '`' or text[-1:] == '`' or (text[:1] == ' ' and text[-1:] == ' '):
        text = ' ' + text + ' '
    return fence + text + fence


def cell(value):
    """The words a slot shows for one record value."""
    if absent(value):
        return NOT_RECORDED
    if any(path_like(flatten(text)) for text in strings(value)):
        return WITHHELD
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return span(flatten(value))


def get(node, *path):
    for key in path:
        if isinstance(key, int):
            if not isinstance(node, list) or key >= len(node):
                return MISSING
        elif not isinstance(node, dict) or key not in node:
            return MISSING
        node = node[key]
    return node


# ---- reading the records ------------------------------------------------------------------------

def read(path, role):
    try:
        return Path(path).read_bytes()
    except OSError:
        raise Refusal('cannot read ' + role)


def decode(data, role):
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        raise Refusal(role + ' is not UTF-8')


def load(data, role):
    def pairs(items):
        seen = set()
        for key, _ in items:
            if key in seen:
                raise Refusal('%s repeats the key %s' % (role, json.dumps(key)))
            seen.add(key)
        return dict(items)

    def constant(name):
        raise Refusal(role + ' holds a non-finite number')

    def number(text):
        value = float(text)   # 1e400 overflows to infinity: a value no record holds
        if value != value or value in (float('inf'), float('-inf')):
            raise Refusal(role + ' holds a non-finite number')
        if value == 0.0 and re.search('[1-9]', re.split('[eE]', text)[0]):   # 1e-400 is not zero
            raise Refusal(role + ' holds a number that rounds to zero')
        return value

    try:
        value = json.loads(decode(data, role), object_pairs_hook=pairs, parse_constant=constant,
                           parse_float=number)
    except RecursionError:
        raise Refusal(role + ' is nested too deeply')
    except ValueError:
        raise Refusal(role + ' is not valid JSON')
    if not isinstance(value, dict):
        raise Refusal(role + ' is not a JSON object')
    return value


def check_manifest(m, role):
    """A present group of the wrong JSON type is refused, never rendered or guessed around."""
    for key in ('predicate_facts', 'reference', 'command', 'params'):
        if not absent(m.get(key, MISSING)) and not isinstance(m[key], dict):
            raise Refusal('%s: %s must be a JSON object' % (role, key))
    for key in ('model_steps', 'containers', 'software_versions'):
        value = m.get(key, MISSING)
        if absent(value):
            continue
        if not isinstance(value, list):
            raise Refusal('%s: %s must be a JSON array' % (role, key))
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                raise Refusal('%s: %s[%d] must be a JSON object' % (role, key, i))
    files = m.get('software_versions', MISSING)
    for i, entry in enumerate(files if isinstance(files, list) else []):
        if not absent(entry.get('versions', MISSING)) and not isinstance(entry['versions'], dict):
            raise Refusal('%s: software_versions[%d].versions must be a JSON object' % (role, i))
    seeds = m.get('random_seeds', MISSING)
    if not absent(seeds):
        if not isinstance(seeds, (list, str)):
            raise Refusal('%s: random_seeds must be a JSON array or string' % role)
        for i, item in enumerate(seeds if isinstance(seeds, list) else []):
            if not isinstance(item, dict):
                raise Refusal('%s: random_seeds[%d] must be a JSON object' % (role, i))


def check_approval(approval, plan_bytes):
    digest = approval.get('plan_sha256', MISSING)
    if absent(digest):
        raise Refusal('approval record has no plan_sha256')
    if not isinstance(digest, str) or not DIGEST.match(digest):
        raise Refusal('approval record plan_sha256 is not 64 hex digits')
    if digest != hashlib.sha256(plan_bytes).hexdigest():
        raise Refusal('approval record does not bind this plan (sha256 differs)')
    stamp = approval.get('timestamp', MISSING)
    if not absent(stamp):
        try:
            if not isinstance(stamp, str) or not UTC.match(stamp):
                raise ValueError(stamp)
            datetime.datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            raise Refusal('approval record timestamp is not a UTC instant')
    actor = approval.get('actor', MISSING)
    if not absent(actor) and not isinstance(actor, str):
        raise Refusal('approval record actor is not a string')


def fence_opening(line):
    """The fence a line opens, as CommonMark reads it, or None: at most three spaces of indent, then
    three or more backticks or tildes; a backtick fence's info string may hold no backtick."""
    bare = line.lstrip(' ')
    if len(line) - len(bare) > 3 or bare[:3] not in ('```', '~~~'):
        return None
    run = len(bare) - len(bare.lstrip(bare[0]))
    if bare[0] == '`' and '`' in bare[run:]:
        return None
    return bare[:run]


def closes(line, fence):
    """A closing fence: at most three spaces, a run of the same character at least as long, then
    only spaces or tabs."""
    bare = line.lstrip(' ')
    body = bare.rstrip(' \t')
    return (len(line) - len(bare) <= 3 and len(body) >= len(fence) and
            body == fence[0] * len(body))


def history_entries(text):
    """`## <date> — <stage> — <outcome>` entries outside fenced blocks, with their Model and
    Template version lines. HISTORY.md's own header shows the entry format inside a fence, and an
    unclosed fence runs to the end, as in CommonMark."""
    entries, fence, current = [], None, None
    for line in text.split('\n'):
        if line.endswith('\r'):
            line = line[:-1]
        if fence is not None:
            if closes(line, fence):
                fence = None
            continue
        fence = fence_opening(line)
        if fence is not None:
            current = None
            continue
        match = ENTRY.match(line)
        if match:
            current = {'date': match.group(1), 'stage': match.group(2), 'outcome': match.group(3),
                       'model': MISSING, 'template_version': MISSING}
            entries.append(current)
        elif line.startswith('#'):
            current = None
        elif current is not None:
            for field, label in (('model', 'Model: '), ('template_version', 'Template version: ')):
                if line.startswith(label) and current[field] is MISSING:
                    current[field] = line[len(label):].rstrip()
    return entries


def approved_stage(approval):
    """`03_custom_analysis/<slug>` from the approval record's plan_path, which is never printed."""
    path = approval.get('plan_path')
    parts = path.split('/') if isinstance(path, str) else []
    if len(parts) >= 3 and parts[-1] == 'PLAN.md' and parts[-3] == '03_custom_analysis':
        return '03_custom_analysis/' + parts[-2]
    return None


# ---- the page -----------------------------------------------------------------------------------

class Page(object):
    def __init__(self):
        self.lines = dict((section, []) for section in (PARAGRAPH, PARAMETERS, SOFTWARE, CITATION, RECORDS))

    def add(self, kind, *slots):
        """slots: (v, ref, value) a record value; (p, ref, actor) the approver phrase;
        (a, ref) a field stated as not recorded; (x, ref) consulted, never printed."""
        words, refs = [], []
        for slot in slots:
            refs.append(slot[1])
            if slot[0] == 'v':
                words.append(cell(slot[2]))
            elif slot[0] == 'p':
                words.append(NO_APPROVER if absent(slot[2]) else BY_APPROVER)
        section, text = KINDS[kind]
        self.lines[section].append((text.format(*words), kind, refs))

    def record(self, name, label, data):
        section, text = KINDS['record']
        self.lines[section].append((text.format(label, span(hashlib.sha256(data).hexdigest())),
                                    'record', [name + ':bytes']))

    def text(self):
        out, sources = [], []
        for section in (PARAGRAPH, PARAMETERS, SOFTWARE, CITATION, RECORDS):
            out += [section, '']
            for line, kind, refs in self.lines[section]:
                out.append(line)
                sources.append('- line %d: %s%s.' % (len(out), kind, ': `%s`' % ' '.join(refs) if refs else ''))
            out.append('')
        return '\n'.join(out + [SOURCES, ''] + sources) + '\n'


def manifest_lines(page, m, k):
    M = 'manifest%d:' % k
    name = get(m, 'workflow_name')

    def v(*path):
        return ('v', M + '/' + '/'.join(str(p) for p in path), get(m, *path))

    page.add('workflow', v('workflow_name'), v('workflow_version'), v('pipeline_commit'), v('wrapper'),
             v('gars_commit'), v('template_version'), v('predicate_facts', 'status'))
    if not absent(get(m, 'failure_class')):
        page.add('failure', v('failure_class'))
    reference = get(m, 'reference')
    if absent(reference):
        page.add('reference-absent', ('a', M + '/reference'))
    else:
        page.add('reference', v('reference', 'build'), v('reference', 'annotation_release'),
                 v('reference', 'fasta_sha256'), v('reference', 'gtf_sha256'))
        if reference.get('comparison') != 'matched':
            # the registry's hashes print above; the hashes of the files the run used print here
            page.add('reference-check', v('reference', 'comparison'), v('reference', 'reason'),
                     v('reference', 'observed', 'fasta_sha256'), v('reference', 'observed', 'gtf_sha256'))
    page.add('config', v('config_sha256'))
    page.add('threads', v('threads'))
    if absent(get(m, 'command')):
        page.add('command-absent', ('a', M + '/command'))
    else:
        page.add('command', v('command', 'path'), v('command', 'sha256'))
    page.add('agent', v('agent_model'))
    steps = get(m, 'model_steps')
    if absent(steps):
        if get(m, 'agent_model') != 'none':
            page.add('model-steps-absent', ('a', M + '/model_steps'))
    else:
        for i, step in enumerate(steps):
            prompt = v('model_steps', i, 'prompt_sha256')
            if isinstance(step.get('prompt_sha256'), dict):
                prompt = v('model_steps', i, 'prompt_sha256', 'value')
            page.add('model-step', v('model_steps', i, 'model_id'), v('model_steps', i, 'provider'),
                     v('model_steps', i, 'prompt_id'), prompt,
                     v('model_steps', i, 'prompt_sha256', 'algorithm'))   # read, never assumed

    label = ('v', M + '/workflow_name', name)
    params = get(m, 'params')
    if absent(params):
        page.add('params-absent', label, ('a', M + '/params'))
    else:
        for j, key in enumerate(sorted(params)):
            page.add('param', label, ('v', '%s/params#%d.key' % (M, j), key),
                     ('v', '%s/params#%d.value' % (M, j), params[key]))
    seeds = get(m, 'random_seeds')
    if absent(seeds):
        page.add('seeds-absent', label, ('a', M + '/random_seeds'))
    elif isinstance(seeds, str):
        page.add('seeds-text', label, v('random_seeds'))
    else:
        for i, seed in enumerate(seeds):
            if absent(seed.get('seed', MISSING)):
                page.add('seed-unset', label, v('random_seeds', i, 'call'), v('random_seeds', i, 'seed_supported'),
                         v('random_seeds', i, 'determinism'), ('a', '%s/random_seeds/%d/seed' % (M, i)))
            else:
                page.add('seed', label, v('random_seeds', i, 'call'), v('random_seeds', i, 'seed'))

    page.add('gars', v('gars_commit'), v('template_version'), label)
    page.add('workflow-version', label, v('workflow_version'), v('pipeline_commit'))
    files = get(m, 'software_versions')
    if absent(files):
        page.add('versions-absent', label, ('a', M + '/software_versions'))
    else:
        for i, entry in enumerate(files):
            P = '%s/software_versions/%d' % (M, i)
            page.add('versions-file', label, v('software_versions', i, 'path'), v('software_versions', i, 'sha256'))
            versions = entry.get('versions', MISSING)
            if absent(versions):
                page.add('version-absent', ('a', P + '/versions'))
            else:
                for j, key in enumerate(sorted(versions)):
                    page.add('version', ('v', '%s/versions#%d.key' % (P, j), key),
                             ('v', '%s/versions#%d.value' % (P, j), versions[key]))
    containers = get(m, 'containers')
    if absent(containers):
        page.add('containers-absent', label, ('a', M + '/containers'))
    else:
        for i in range(len(containers)):
            page.add('container', label, v('containers', i, 'process'), v('containers', i, 'image'),
                     v('containers', i, 'digest'), v('containers', i, 'image_sha256'))


def render(manifests, plan=None, approval=None, history=None):
    """Validate every named input, then build the page; a refusal writes nothing."""
    records, loaded = [], []
    for k, path in enumerate(manifests, 1):
        data = read(path, 'manifest %d' % k)
        manifest = load(data, 'manifest %d' % k)
        check_manifest(manifest, 'manifest %d' % k)
        records.append(('manifest%d' % k, 'manifest %d' % k, data))
        loaded.append(manifest)
    approved, entries = None, None
    if plan is not None:
        plan_bytes = read(plan, 'plan')
        approval_bytes = read(approval, 'approval record')
        approved = load(approval_bytes, 'approval record')
        check_approval(approved, plan_bytes)
        records += [('plan', 'plan', plan_bytes), ('approval', 'approval record', approval_bytes)]
        if history is not None:
            history_bytes = read(history, 'history')
            entries = history_entries(decode(history_bytes, 'history'))
            records.append(('history', 'history', history_bytes))

    page = Page()
    for k, manifest in enumerate(loaded, 1):
        try:
            manifest_lines(page, manifest, k)
        except RecursionError:   # a value nested deeper than a JSON reader of this Python parses
            raise Refusal('manifest %d is nested too deeply' % k)
    if approved is not None:
        page.add('approval', ('v', 'approval:/plan_sha256', approved.get('plan_sha256', MISSING)),
                 ('v', 'approval:/timestamp', approved.get('timestamp', MISSING)),
                 ('p', 'approval:/actor?', approved.get('actor', MISSING)))
        if entries is not None:
            stage = approved_stage(approved)
            matched = [(e, entry) for e, entry in enumerate(entries)
                       if stage is not None and entry['stage'] == stage and entry['outcome'] == 'analysis complete']
            for e, entry in matched:
                page.add('history', *(('v', 'history:#%d/%s' % (e, field), entry[field])
                                      for field in ('stage', 'outcome', 'date', 'model', 'template_version')))
            if not matched:
                page.add('history-absent', ('x', 'history:entries'), ('x', 'approval:/plan_path?'))
    page.add('pointer')
    cited = []
    for k, manifest in enumerate(loaded, 1):
        commit = get(manifest, 'gars_commit')
        if absent(commit):
            page.add('citation-absent', ('v', 'manifest%d:/workflow_name' % k, get(manifest, 'workflow_name')),
                     ('a', 'manifest%d:/gars_commit' % k))
        elif cell(commit) not in cited:
            cited.append(cell(commit))
            page.add('citation', ('v', 'manifest%d:/gars_commit' % k, commit))
    for name, label, data in records:
        page.record(name, label, data)
    return page.text()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--manifest', type=Path, action='append', required=True)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--approval', type=Path)
    parser.add_argument('--history', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if (args.plan is None) != (args.approval is None):
        parser.error('--plan and --approval come together')
    if args.history is not None and args.approval is None:
        parser.error('--history needs --plan and --approval')
    named = [('manifest %d' % k, path) for k, path in enumerate(args.manifest, 1)]
    named += [(role, path) for role, path in (('plan', args.plan), ('approval record', args.approval),
                                              ('history', args.history)) if path is not None]
    temporary = None
    try:
        for role, path in named:   # a record is never replaced by the page rendered from it
            if os.path.realpath(str(path)) == os.path.realpath(str(args.out)):
                raise Refusal('the output would overwrite ' + role)
            # The same file under another spelling: a case variant on a case-insensitive
            # filesystem, a Unicode-normalization variant, or a hard link (device and inode).
            if os.path.exists(str(args.out)) and os.path.exists(str(path)) and \
                    os.path.samefile(str(path), str(args.out)):
                raise Refusal('the output would overwrite ' + role)
        data = render(args.manifest, args.plan, args.approval, args.history).encode('utf-8')
        with tempfile.NamedTemporaryFile(mode='wb', prefix='.methods-', dir=str(args.out.parent),
                                         delete=False) as fh:
            temporary = fh.name
            fh.write(data)
        try:   # the page is written to be shared: keep the output's mode, or the umask's for a new one
            mode = os.stat(str(args.out)).st_mode & 0o777
        except OSError:
            umask = os.umask(0)
            os.umask(umask)
            mode = 0o666 & ~umask
        os.chmod(temporary, mode)
        os.replace(temporary, str(args.out))
        temporary = None
    except Refusal as exc:
        print('methods refused: ' + str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print('methods refused: cannot write the output (%s)' % type(exc).__name__, file=sys.stderr)
        return 1
    finally:
        if temporary:
            os.unlink(temporary)
    return 0


if __name__ == '__main__':
    sys.exit(main())
