"""Reference launcher. The calling OS account supplies reviewer identity, never a flag."""
import argparse
import datetime
import hashlib
import json
import os
import pwd
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import uuid
from pathlib import Path
from common import PROMPT_PATH, git, read_json, sha256, within, write_json
from review_record import invalid_reasons, review_errors

# Lane specification item 8 supplies this deployment signature, not another runner.
LIMIT = re.compile(r"^(?:You['\u2019]ve hit your (?:session |weekly )?limit\b|Claude usage limit reached\.)")
FORBIDDEN = ('review', 'fault', 'case', 'measure', 'plant', 'eval')


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def host_digest():
    path = Path(os.path.join(os.sep, 'etc', 'machine-id'))
    try:
        value = path.read_bytes()
    except FileNotFoundError:
        value = socket.gethostname().encode('utf-8')
    return sha256(value)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            for text in strings(item):
                yield text
    elif isinstance(value, list):
        for item in value:
            for text in strings(item):
                yield text


def tool_inputs(value):
    if isinstance(value, dict):
        if value.get('type') == 'tool_use':
            yield value.get('name'), value.get('input', {})
        for item in value.values():
            for data in tool_inputs(item):
                yield data
    elif isinstance(value, list):
        for item in value:
            for data in tool_inputs(item):
                yield data


def session_output_store(kit, session_id):
    """Item 19: only this launch's saved tool output, never the project store."""
    project = re.sub(r'[^a-zA-Z0-9-]', '-', str(Path(kit).resolve()))
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    return home / '.claude' / 'projects' / project / session_id / 'tool-results'


def input_fields(value, field=None):
    """Retain field names so content and prose can be excluded before parsing."""
    if isinstance(value, str):
        yield field, value
    elif isinstance(value, dict):
        for key, item in value.items():
            for pair in input_fields(item, key):
                yield pair
    elif isinstance(value, list):
        for item in value:
            for pair in input_fields(item, field):
                yield pair


def removal_line_is_unambiguous(text, index):
    """Item 23: substitution or arithmetic anywhere on this line forbids removal."""
    start = text.rfind('\n', 0, index) + 1
    end = text.find('\n', index)
    line = text[start:] if end < 0 else text[start:end]
    return not any(cue in line for cue in ('$(', '`', '(('))


def shell_syntax(text, state=(None, True)):
    """Keep source quoting for comments and real heredoc operators.

    shlex removes quotes and recognizes comments inside words; neither behavior
    can decide these two shell boundaries. Preserve offsets and newlines here.
    """
    quote, word_start = state
    cleaned = list(text)
    heredocs = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '\\' and quote != "'":
            if index + 1 < len(text) and text[index + 1] != '\n':
                word_start = False
            index += 2
            continue
        if quote:
            if char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
            word_start = False
        elif char == '#' and word_start and removal_line_is_unambiguous(text, index):
            end = text.find('\n', index)
            end = len(text) if end < 0 else end
            cleaned[index:end] = ' ' * (end - index)
            index = end
            continue
        elif char in '<>':
            end = index + 1
            while end < len(text) and text[end] in '<>':
                end += 1
            if text[index:end] == '<<' and removal_line_is_unambiguous(text, index):
                heredocs.append(index)
            index = end
            word_start = True
            continue
        else:
            word_start = char.isspace() or char in ';&|()'
        index += 1
    return ''.join(cleaned), heredocs, (quote, word_start)


def shell_words(text):
    cleaned, operators, state = shell_syntax(text)
    lexer = shlex.shlex(cleaned, posix=True, punctuation_chars=';&|<>()\n')
    lexer.whitespace = ' \t\r'
    lexer.whitespace_split = True
    lexer.commenters = ''
    return list(lexer)


def path_field(field):
    return field in ('path', 'file', 'directory', 'filename', 'cwd') or bool(
        field and field.endswith(('_path', '_paths', '_file', '_files', '_directory')))


def bare_directory_change(text):
    """Item 20(b)(iv): inspect shell words, including prefix options and escapes."""
    words = [word for word, scan_root in audit_words(text)]
    for index, word in enumerate(words):
        if word == 'cd':
            arguments = []
            cursor = index + 1
            redirects = ('<', '>', '>>', '<<', '<<<', '<&', '>&', '<>', '>|', '&>', '&>>', '<<-')
            while cursor < len(words):
                argument = words[cursor]
                # Numeric and named descriptors are not cd arguments (Y1 F1, Y2 F1).
                descriptor = argument.isdigit() or re.fullmatch(r'\{[A-Za-z_][A-Za-z0-9_]*\}', argument)
                if descriptor and cursor + 1 < len(words) and words[cursor + 1] in redirects:
                    cursor += 1
                    argument = words[cursor]
                if argument in redirects:
                    cursor += 2
                    continue
                if argument and all(c in ';&|<>()\n' for c in argument):
                    break
                arguments.append(argument)
                cursor += 1
            if all(argument.startswith('-') for argument in arguments):
                return True
    return False


def without_heredocs(text):
    """Items 22(c), 23: remove only unambiguous bodies with confirmed closers."""
    result = []
    state = (None, True)
    lines = text.splitlines(True)
    cursor = 0
    while cursor < len(lines):
        line = lines[cursor]
        cursor += 1
        cleaned, operators, state = shell_syntax(line, state)
        result.append(cleaned)
        pending = []
        # Headers can contain quotes continued on later lines. The full shell
        # parser below, rather than this header inspection, diagnoses errors.
        for index in operators:
            tail = cleaned[index + 2:].rstrip('\r\n')
            tabs = tail.startswith('-')
            if tabs:
                tail = tail[1:]
            try:
                words = shell_words(tail)
            except ValueError:
                pending = []
                break
            # A control or redirect operator cannot stand in for a delimiter.
            if not words or (words[0] and all(c in ';&|<>()\n' for c in words[0])):
                pending = []
                break
            pending.append((words[0], tabs))
        end = cursor
        for delimiter, tabs in pending:
            while end < len(lines):
                candidate = lines[end].rstrip('\r\n')
                if tabs:
                    candidate = candidate.lstrip('\t')
                end += 1
                if candidate == delimiter:
                    break
            else:
                # No removal at all unless every queued body has its closer.
                end = cursor
                break
        cursor = end
    return ''.join(result)


def audit_words(text):
    """Yield visible shell words and whether the separator rule applies.

    Item 22 separates program data from file operands before either path rule.
    Shell programs recurse; interpreter text retains the earlier token audit.
    This is a bounded syntax audit, never an evaluator or sandbox.
    """
    words = shell_words(without_heredocs(text))
    command = None
    argument = None
    prefix = None
    program_pending = False
    option_end = False
    text_commands = ('awk', 'gawk', 'mawk', 'sed', 'grep', 'egrep', 'fgrep', 'rg')
    shells = ('sh', 'bash', 'dash', 'zsh', 'ksh')
    prefix_options = {
        'env': ('-u', '--unset', '-C', '--chdir', '-S', '--split-string'),
        'exec': ('-a',), 'time': ('-o', '--output', '-f', '--format'),
        'timeout': ('-s', '--signal', '-k', '--kill-after'),
        'nice': ('-n', '--adjustment'), 'stdbuf': ('-i', '-o', '-e'),
        'command': (), 'builtin': (), 'eval': (), 'nohup': ()}
    for word in words:
        option_value = False
        command_word = False
        if argument:
            previous_argument = argument
            argument = None
            if previous_argument == 'shell':
                yield ';', True
                for pair in audit_words(word):
                    yield pair
                yield ';', True
                continue
            if previous_argument == 'interpreter':
                for token in re.findall(r"[^\s\"'`;|<>()\[\],=]+", word):
                    yield token, False
                continue
            if previous_argument == 'delimiter':
                yield word, False
                continue
            if previous_argument != 'path':
                continue
            option_value = True
        if word and all(c in ';&|<>()\n' for c in word):
            # Redirection targets are operands, even after echo or printf.
            if '<' in word or '>' in word:
                argument = 'path'
            else:
                command = prefix = None
                program_pending = option_end = False
            yield word, True
            continue
        if command is None and not option_value:
            name = os.path.basename(word)
            if prefix and word in prefix_options[prefix]:
                argument = 'path'
                yield word, True
                continue
            if prefix and (word.startswith('-') or '=' in word or
                           re.fullmatch(r'[0-9]+(?:[.][0-9]+)?[smhd]?', word)):
                yield word, True
                continue
            if word in ('if', 'then', 'do', 'else', '{'):
                yield word, True
                continue
            if name in prefix_options:
                prefix = name
                yield word, True
                continue
            command = name
            command_word = True
            program_pending = command in text_commands
        if not command_word and not option_value:
            if command in shells and re.fullmatch(r'-[a-zA-Z]*c', word):
                argument = 'shell'
                continue
            if word in ('-c', '-e') and command and re.fullmatch(r'(?:python[0-9.]*|perl|ruby|node)', command):
                argument = 'interpreter'
                continue
            delimiters = (('-F', '--field-separator') if command in ('awk', 'gawk', 'mawk') else
                          ('-d', '--delimiter') if command == 'cut' else ())
            if word in delimiters:
                argument = 'delimiter'
                continue
            attached = next((word[len(option) + 1:] if option.startswith('--') else word[len(option):]
                             for option in delimiters if
                             (word.startswith(option + '=') if option.startswith('--') else
                              word.startswith(option) and len(word) > len(option))), None)
            if attached is not None:
                yield attached, False
                continue
        # Item 22(a): neither path rule applies to these data contexts.
        if not command_word and not option_value:
            if command in ('printf', 'echo'):
                continue
            if command == 'git' and word.startswith(('--format=', '--pretty=format:', '--pretty=tformat:')):
                continue
            if command in text_commands:
                if not option_end and word == '--':
                    option_end = True
                    continue
                if not option_end and word in ('--files', '--type-list') and command == 'rg':
                    program_pending = False
                    continue
                if not option_end and word in ('-e', '--expression', '--regexp', '--source'):
                    program_pending = False
                    argument = 'code'
                    continue
                if not option_end and word in ('-f', '--file'):
                    program_pending = False
                    argument = 'path'
                    continue
                if not option_end and word.startswith(('--expression=', '--regexp=', '--source=')):
                    program_pending = False
                    continue
                if not option_end and word.startswith('--file='):
                    program_pending = False
                # Short option clusters: e/f consume the rest, or the next word.
                cluster = (re.search('[ef]', word[1:]) if not option_end and
                           word.startswith('-') and not word.startswith('--') else None)
                if cluster:
                    program_pending = False
                    offset = cluster.start() + 2
                    kind = 'code' if cluster.group() == 'e' else 'path'
                    if len(word) == offset:
                        argument = kind
                    elif kind == 'path':
                        yield word[offset:], True
                    continue
                if not option_end and word in (('-v', '--assign') if command in ('awk', 'gawk', 'mawk') else ()):
                    argument = 'path'
                    continue
                if not option_end and word in ('-A', '-B', '-C', '-m', '--max-count', '--context',
                                              '--after-context', '--before-context', '-g', '--glob', '-t', '--type'):
                    argument = 'path'
                    continue
                if program_pending and (option_end or not word.startswith('-')):
                    program_pending = False
                    continue
        yield word, True


def root_word_hits(text, field):
    """Separator-only operands are hits; data contexts are removed upstream."""
    if field != 'command' and not path_field(field):
        return 0
    words = audit_words(text) if field == 'command' else [(text, True)]
    hits = 0
    for word, scan_root in words:
        if not scan_root:
            continue
        candidate = word
        if '=' in word:
            candidate = word.partition('=')[2]
        elif re.match(r'^-[a-zA-Z]+' + re.escape(os.sep), word):
            candidate = re.sub(r'^-[a-zA-Z]+', '', word)
        pieces = [candidate]
        pieces = [piece[1:] if piece.startswith('$') else piece for piece in pieces]
        hits += sum(1 for piece in pieces if piece and not piece.strip(os.sep))
    return hits


def blindness(events, kit, session_id=None):
    """Lane specification item 20: bounded audit, separate from sandbox enforcement.

    Resolve symlinks as well as lexical parent steps. Shell syntax is tokenized,
    never executed. Only command and path-valued fields are scanned (item 22).
    """
    kit = Path(kit).resolve()
    saved_output = session_output_store(kit, session_id) if session_id else None
    trees = [Path(os.path.join(os.sep, x)) for x in ('usr', 'bin', 'sbin', 'lib', 'lib64')]
    devices = [Path(os.path.join(os.sep, 'dev', x)) for x in ('null', 'stdin', 'stdout', 'stderr')]
    calls = hits = 0
    for event in events:
        for tool, data in tool_inputs(event):
            calls += 1
            for field, text in input_fields(data):
                if tool == 'Glob' and field == 'pattern':
                    field = 'path'
                if field != 'command' and not path_field(field):
                    continue
                try:
                    decoded = [word for word, scan_root in audit_words(text)] if field == 'command' else [text]
                    hits += root_word_hits(text, field)
                except ValueError:
                    hits += 1
                    continue
                tokens = list(dict.fromkeys(decoded))
                parent = chr(46) * 2
                home = '$' + 'HOME'
                brace_home = '$' + '{HOME}'
                bare_cd = field == 'command' and bare_directory_change(text)
                if bare_cd:
                    hits += 1
                for token in tokens:
                    if ((field == 'command' and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*=', token)) or
                            (token.startswith('-') and '=' in token)):
                        token = token.partition('=')[2]
                    elif re.match(r'^-[a-zA-Z]+' + re.escape(os.sep), token):
                        token = re.sub(r'^-[a-zA-Z]+', '', token)
                    elif token.startswith('-'):
                        option = re.match(r'^-[a-zA-Z]+', token)
                        if option and token[option.end():].startswith((parent, chr(126), '$')):
                            token = token[option.end():]
                    # Root-only tokens were classified with field and shell-word context.
                    if token and not token.strip(os.sep):
                        continue
                    expansion = re.search(r'\$\{(?:HOME|PWD)(?=[^a-zA-Z0-9_])[^}]*\}?', token)
                    candidate = (os.path.isabs(token) or token.startswith((chr(126), home, brace_home)) or
                                 parent in token.split('/') or expansion or token.startswith('$' + 'PWD'))
                    if not candidate:
                        continue
                    if expansion:
                        variable = expansion.group()
                        if variable not in (brace_home, '$' + '{PWD}'):
                            # Shell modifiers are not evaluated by this static scan.
                            hits += 1
                            continue
                        value = pwd.getpwuid(os.getuid()).pw_dir if variable == brace_home else str(kit)
                        token = token.replace(variable, value)
                    elif token.startswith('$' + 'PWD'):
                        token = str(kit) + token[len('$' + 'PWD'):]
                    # Unknown variable expansion cannot establish kit containment.
                    if '$' in token and parent in token.split('/'):
                        hits += 1
                        continue
                    if token.startswith((home, brace_home)):
                        prefix = brace_home if token.startswith(brace_home) else home
                        token = pwd.getpwuid(os.getuid()).pw_dir + token[len(prefix):]
                    elif token.startswith(chr(126)):
                        user, separator, suffix = token[1:].partition(os.sep)
                        try:
                            account = pwd.getpwnam(user) if user else pwd.getpwuid(os.getuid())
                            token = os.path.join(account.pw_dir, suffix)
                        except KeyError:
                            hits += 1
                            continue
                    path = Path(token) if os.path.isabs(token) else kit / token
                    if within(path, kit):
                        continue
                    if saved_output is not None and within(path, saved_output):
                        continue
                    if any(within(path, tree) for tree in trees) or path in devices:
                        continue
                    hits += 1
    return {'calls': calls, 'hits': hits}


def parse_stream(raw):
    events = []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        events.append(event)
    return events


def stream_facts(events, raw):
    models = []
    message_models = []
    limit = any(LIMIT.match(line.strip()) for line in raw.splitlines())
    for event in events:
        for text in strings(event):
            if any(LIMIT.match(line.strip()) for line in text.splitlines()):
                limit = True
        if isinstance(event, dict) and isinstance(event.get('message'), dict):
            reported = event['message'].get('model')
            if reported and reported != '<synthetic>':
                message_models.append(reported)
        if isinstance(event, dict) and event.get('type') == 'system' and event.get('subtype') == 'init':
            model = event.get('model')
            if model and model != '<synthetic>':
                models.append(model)
    return (models + message_models if models else []), limit


def safe_review(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'r', encoding='utf-8') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('review.json must be a regular file owned by reviewer')
        return json.load(stream)


def launch_identity(producer_account):
    uid = os.getuid()
    if uid == 0:
        raise ValueError('privileged reviewer refused')
    try:
        producer = pwd.getpwnam(producer_account)
    except KeyError:
        raise ValueError('producer-account does not resolve on this host')
    if uid == producer.pw_uid:
        raise ValueError('producer and reviewer uid must differ')
    return ({'uid': uid, 'os_user': pwd.getpwuid(uid).pw_name},
            {'uid': producer.pw_uid, 'os_user': producer.pw_name})


def clean_environment(kit):
    env = {k: v for k, v in os.environ.items()
           if not ((k.startswith('CLAUDE') and k != 'CLAUDE_CODE_OAUTH_TOKEN') or
                   k.startswith('ANTHROPIC_') or k.startswith('TMP') or k.startswith('TEMP'))}
    for key in ('TMPDIR', 'TEMP', 'TMP'):
        env[key] = str(kit / 'tmp')
    return env


def next_attempt(records, neutral):
    first = records / (neutral + '.record.json')
    if not first.exists():
        if list(records.glob(neutral + '.attempt*.record.json')):
            raise ValueError('attempts without first record')
        return 1, first, records / (neutral + '.stream.jsonl')
    attempts = [(1, first)]
    for path in records.glob(neutral + '.attempt*.record.json'):
        match = re.fullmatch(re.escape(neutral) + r'\.attempt([2-9][0-9]*|1[0-9]+)\.record\.json', path.name)
        if not match:
            raise ValueError('invalid attempt filename')
        attempts.append((int(match.group(1)), path))
    number, path = max(attempts)
    if not read_json(path)['envelope']['ended_on_usage_limit']:
        raise ValueError('existing record is never overwritten; only usage-limit attempts resume')
    number += 1
    stem = neutral + '.attempt%d' % number
    return number, records / (stem + '.record.json'), records / (stem + '.stream.jsonl')


def run(args):
    reviewer, producer = launch_identity(args.producer_account)
    if 'ANTHROPIC_API_KEY' in os.environ:
        raise ValueError('ANTHROPIC_API_KEY must be unset')
    if not args.model:
        raise ValueError('model required')
    if not args.settings:
        raise ValueError('sandbox settings required')
    settings = Path(args.settings).read_bytes()
    manifest = read_json(args.manifest)
    prompt = Path(args.prompt).read_bytes()
    if sha256(prompt) != manifest['prompt_sha256'] or manifest['prompt_path'] != PROMPT_PATH:
        raise ValueError('prompt does not match manifest')
    ids = manifest['cases']
    if len(ids) != len(set(ids)) or not all(re.fullmatch('[0-9a-f]{12}', n) for n in ids):
        raise ValueError('invalid manifest case ids')
    only = args.only.split(',') if args.only else ids
    if not set(only).issubset(ids):
        raise ValueError('only names an unknown case')
    selected = [n for n in ids if n in only]
    kits = Path(args.kits_root).resolve()
    records = Path(args.records).resolve()
    if within(records, kits) or within(args.cases, kits):
        raise ValueError('private inputs and records must stay outside kits-root')
    records.mkdir(parents=True, exist_ok=True)
    kits.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output(['claude', '--version'], env=clean_environment(kits)).decode().strip()
    if not version:
        raise ValueError('tool version missing')
    for index, neutral in enumerate(selected):
        attempt, output, stream_path = next_attempt(records, neutral)
        kit = kits / neutral
        if kit.exists():
            raise ValueError('kit exists; resume with a fresh neutral kits-root')
        neutral_components = (neutral, 'repo', 'tmp', '.claude')
        if any(word in component.lower() for component in neutral_components for word in FORBIDDEN):
            raise ValueError('created kit directories must have neutral path components')
        kit.mkdir()
        (kit / 'tmp').mkdir()
        git(kit, 'clone', '--no-local', '--quiet', str(Path(args.cases).resolve() / neutral / 'repo'), 'repo')
        repo = kit / 'repo'
        git(repo, 'remote', 'remove', 'origin')
        git(repo, 'reflog', 'expire', '--expire=all', '--all')
        (kit / 'BRIEF.md').write_bytes(prompt)
        (kit / '.claude').mkdir()
        (kit / '.claude/settings.json').write_bytes(settings)
        if (kit / '.claude/settings.json').read_bytes() != settings:
            raise ValueError('settings copy differs')
        if kit == (repo / '.claude').resolve():
            raise ValueError('repository settings directory cannot be cwd')
        head = git(repo, 'rev-parse', 'HEAD').decode().strip()
        parent = git(repo, 'rev-parse', 'HEAD~1').decode().strip()
        session = str(uuid.uuid4())
        started = now()
        host = host_digest()
        argv = ['claude', '-p', 'Read BRIEF.md in this folder and follow it exactly. Write review.json in this folder.',
                '--model', args.model, '--permission-mode', 'auto', '--permission-prompts', 'none',
                '--setting-sources', 'project,local', '--strict-mcp-config',
                '--output-format', 'stream-json', '--verbose', '--session-id', session]
        with stream_path.open('xb') as stream, open(os.devnull, 'rb') as stdin:
            result = subprocess.run(argv, cwd=str(kit), env=clean_environment(kit), stdin=stdin,
                                    stdout=stream, stderr=subprocess.STDOUT)
        finished = now()
        raw = stream_path.read_text(encoding='utf-8', errors='replace')
        events = parse_stream(raw)
        models, limit = stream_facts(events, raw)
        try:
            review = safe_review(kit / 'review.json')
        except (OSError, ValueError) as exc:
            review = {'invalid_output': type(exc).__name__}
        # Preserve the submitted output, but use a non-schema review for launch failures.
        # The model cannot supply or replace any envelope field.
        if not models or any(model != args.model for model in models):
            review = {'invalid_model': models, 'submitted_review': review}
        record = {'review': review, 'envelope': {
            'schema_version': 1, 'case': neutral, 'repo_head': head, 'repo_parent': parent,
            'sandbox_settings_sha256': sha256(settings),
            'host_digest': host, 'reviewer': dict(reviewer, model_id=models[0] if models else 'unknown',
                prompt_path=PROMPT_PATH, prompt_sha256=sha256(prompt), session_id=session,
                tool='claude', tool_version=version, login_entry=args.login_entry, attempt=attempt),
            'producer': producer, 'started_at': started, 'finished_at': finished,
            'exit_code': result.returncode, 'ended_on_usage_limit': limit,
            'blindness': blindness(events, kit, session)}}
        write_json(output, record)
        errors = invalid_reasons(record, manifest)
        print(neutral + ': ' + ('INVALID: ' + '; '.join(errors) if errors else 'VALID'))
        if limit:
            print('remaining: ' + ','.join(selected[index + 1:]))
            print('resume current: ' + neutral + ' (new login, fresh neutral kits-root)')
            return 0
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cases', 'manifest', 'prompt', 'kits-root', 'records', 'model', 'producer-account'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--login-entry', type=int, required=True)
    parser.add_argument('--settings', required=True)
    parser.add_argument('--only')
    args = parser.parse_args(argv)
    try:
        if args.login_entry < 0:
            raise ValueError('login-entry must be nonnegative')
        return run(args)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print('run reviews: REFUSED (' + str(exc) + ')', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
