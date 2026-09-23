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
            yield value.get('input', {})
        for item in value.values():
            for data in tool_inputs(item):
                yield data
    elif isinstance(value, list):
        for item in value:
            for data in tool_inputs(item):
                yield data


def blindness(events, kit):
    """Lane specification item 8: token paths against kit and system allowlist.

    Resolve symlinks as well as lexical parent steps. Shell syntax is tokenized,
    never executed. Strings nested in tool inputs are all scanned.
    """
    kit = Path(kit).resolve()
    trees = [Path(os.path.join(os.sep, x)) for x in ('usr', 'bin', 'sbin', 'lib', 'lib64')]
    devices = [Path(os.path.join(os.sep, 'dev', x)) for x in ('null', 'stdin', 'stdout', 'stderr')]
    calls = hits = 0
    for event in events:
        for data in tool_inputs(event):
            calls += 1
            for text in strings(data):
                try:
                    decoded = shlex.split(text)
                except ValueError:
                    hits += 1
                    continue
                # Inspect strings inside quoted shell/interpreter arguments too.
                # Split syntax delimiters, retaining complete relative path tokens.
                tokens = re.findall(r"[^\s\"'`;|<>()\[\],=]+", text)
                tokens = list(dict.fromkeys(decoded + tokens))
                parent = chr(46) * 2
                home = '$' + 'HOME'
                brace_home = '$' + '{HOME}'
                bare_cd = re.search(r"(?:^|[;|&\"'])\s*cd\s*(?=$|[;|&\"'])", text)
                if bare_cd:
                    hits += 1
                for token in tokens:
                    if token.startswith('-') and os.sep in token:
                        token = token[token.index(os.sep):]
                    candidate = (os.path.isabs(token) or token.startswith((chr(126), home, brace_home)) or
                                 parent in token.split('/'))
                    if not candidate:
                        continue
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
        if args.settings:
            settings = Path(args.settings).read_bytes()
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
            'host_digest': host, 'reviewer': dict(reviewer, model_id=models[0] if models else 'unknown',
                prompt_path=PROMPT_PATH, prompt_sha256=sha256(prompt), session_id=session,
                tool='claude', tool_version=version, login_entry=args.login_entry, attempt=attempt),
            'producer': producer, 'started_at': started, 'finished_at': finished,
            'exit_code': result.returncode, 'ended_on_usage_limit': limit,
            'blindness': blindness(events, kit)}}
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
    parser.add_argument('--settings')
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
