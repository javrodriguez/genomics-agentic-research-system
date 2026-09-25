"""Two-phase science launcher. Only resume delivers phase B; envelope is code-owned."""
import argparse
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from bio_common import (PROMPT_PATH, sha256, read_json, write_json, blindness,
    parse_stream, stream_facts, safe_review, launch_identity, clean_environment,
    next_attempt, host_digest, LIMIT, now, rf_run_reviews, validate)
from bio_review_record import invalid_reasons, SCHEMA

FORBIDDEN = rf_run_reviews.FORBIDDEN + ('bio', 'science', 'flaw', 'defect', 'fixture', 'seal')
within = rf_run_reviews.within


def run(args):
    reviewer, producer = launch_identity(args.producer_account)
    if 'ANTHROPIC_API_KEY' in os.environ:
        raise ValueError('ANTHROPIC_API_KEY must be unset')
    if not args.model or not args.settings:
        raise ValueError('model and settings required')
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
    kits, records = Path(args.kits_root).resolve(), Path(args.records).resolve()
    if within(records, kits) or within(args.cases, kits):
        raise ValueError('private inputs and records must stay outside kits-root')
    if any(word in component.lower() for component in kits.parts for word in FORBIDDEN):
        raise ValueError('kit parents must be neutral')
    records.mkdir(parents=True, exist_ok=True)
    kits.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output(['claude', '--version'], env=clean_environment(kits)).decode().strip()
    if not version:
        raise ValueError('tool version missing')
    for index, neutral in enumerate(selected):
        attempt, output, stream_path = next_attempt(records, neutral)
        kit = kits / neutral
        if kit.exists():
            raise ValueError('kit exists; use a fresh neutral kits-root')
        kit.mkdir()
        (kit / 'tmp').mkdir()
        (kit / 'project').mkdir()
        source = Path(args.cases) / neutral / 'project'
        for directory in ('1-design', '2-data', '3-results'):
            shutil.copytree(str(source / directory), str(kit / 'project' / directory))
        (kit / 'BRIEF.md').write_bytes(prompt)
        (kit / '.claude').mkdir()
        (kit / '.claude/settings.json').write_bytes(settings)
        if (kit / '.claude/settings.json').read_bytes() != settings:
            raise ValueError('settings copy differs')
        withheld = not (kit / 'project/4-report').exists()
        if not withheld:
            raise ValueError('narrative present before phase A')
        session = str(uuid.uuid4())
        phases, audits, all_models, notes_errors = [], [], [], []
        notes_hash = sha256(b'')
        review = {'invalid_output': 'phase B not run'}
        for name in ('A', 'B'):
            if name == 'B':
                if phases[0]['ended_on_usage_limit'] or phases[0]['exit_code'] or notes_errors:
                    phases.append(dict(name='B', session_id='not-started', started_at=now(), finished_at=now(),
                        exit_code=1, ended_on_usage_limit=False, blindness={'calls': 0, 'hits': 0}, session_matches_phase_a=False))
                    break
                shutil.copytree(str(source / '4-report'), str(kit / 'project/4-report'))
            message = ('Read BRIEF.md in this folder and follow Phase 1 exactly.' if name == 'A' else
                       'The narrative is now in project/4-report. Follow Phase 2 in BRIEF.md.')
            argv = ['claude', '-p', message, '--model', args.model, '--permission-mode', 'auto',
                    '--permission-prompts', 'none', '--setting-sources', 'project,local',
                    '--strict-mcp-config', '--output-format', 'stream-json', '--verbose',
                    '--session-id' if name == 'A' else '--resume', session]
            destination = stream_path.with_name(stream_path.stem + '.' + name + '.jsonl')
            started = now()
            with destination.open('xb') as stream, open(os.devnull, 'rb') as stdin:
                process = subprocess.run(argv, cwd=str(kit), env=clean_environment(kit), stdin=stdin,
                                         stdout=stream, stderr=subprocess.STDOUT)
            finished = now()
            raw = destination.read_text(encoding='utf-8', errors='replace')
            events = parse_stream(raw)
            models, limit = stream_facts(events, raw)
            all_models.extend(models or ['unknown'])
            own_session = session
            if name == 'B':
                reported = [e.get('session_id') for e in events if isinstance(e, dict)
                            and e.get('type') == 'system' and e.get('subtype') == 'init']
                own_session = reported[0] if len(reported) == 1 and isinstance(reported[0], str) else 'missing-init'
            audit = blindness(events, kit, own_session)
            audits.append(audit)
            phase = dict(name=name, session_id=own_session, started_at=started, finished_at=finished,
                         exit_code=process.returncode, ended_on_usage_limit=limit,
                         blindness={key: audit[key] for key in ('calls', 'hits')})
            if name == 'A':
                try:
                    notes = safe_review(kit / 'notes.json')
                    note_schema = {'type': 'object', 'required': ['findings'], 'additionalProperties': False,
                        'properties': {'findings': SCHEMA['properties']['review']['properties']['findings']}}
                    notes_errors = validate(notes, note_schema)
                    notes_hash = sha256((kit / 'notes.json').read_bytes())
                except (OSError, ValueError):
                    notes_errors = ['notes unavailable']
                phase['notes_sha256'] = notes_hash
            else:
                phase['session_matches_phase_a'] = own_session == session
                try:
                    review = safe_review(kit / 'review.json')
                except (OSError, ValueError) as exc:
                    review = {'invalid_output': type(exc).__name__}
            phases.append(phase)
        if any(model != args.model for model in all_models):
            review = {'invalid_model': all_models, 'submitted_review': review}
        if notes_errors:
            review = {'invalid_notes': notes_errors, 'submitted_review': review}
        record = {'review': review, 'envelope': {
            'schema_version': 1, 'case': neutral, 'repo_head': manifest['harness_commit'], 'repo_parent': manifest['base_sha'],
            'sandbox_settings_sha256': sha256(settings), 'host_digest': host_digest(),
            'reviewer': dict(reviewer, model_id=all_models[0] if all_models else 'unknown',
                prompt_path=PROMPT_PATH, prompt_sha256=sha256(prompt), session_id=session,
                tool='claude', tool_version=version, login_entry=args.login_entry, attempt=attempt),
            'producer': producer, 'started_at': phases[0]['started_at'], 'finished_at': phases[-1]['finished_at'],
            'exit_code': next((p['exit_code'] for p in phases if p['exit_code']), 0),
            'ended_on_usage_limit': any(p['ended_on_usage_limit'] for p in phases),
            'blindness': {key: sum(a.get(key, 0) for a in audits) for key in ('calls', 'hits', 'ambiguous')},
            'phases': phases, 'narrative_withheld_until_phase_b': withheld}}
        # Both actual session ids are retained in the envelope; equality is never assumed.
        write_json(output, record)
        errors = invalid_reasons(record, manifest)
        print(neutral + ': ' + ('INVALID: ' + '; '.join(errors) if errors else 'VALID'))
        if record['envelope']['ended_on_usage_limit']:
            print('remaining: ' + ','.join(selected[index + 1:]))
            print('resume current: ' + neutral + ' (new login, fresh neutral kits-root)')
            return 0
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cases', 'manifest', 'prompt', 'kits-root', 'records', 'model', 'producer-account', 'settings'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--login-entry', type=int, required=True)
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
