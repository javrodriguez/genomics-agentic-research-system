"""Science vocabulary and shared row 9 objects, without bare-name collisions."""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE_SHA = 'a77908474f2fc463f481a55f2d0c2ceeee8be660'
PROMPT_PATH = 'gars/_references/prompts/review_faults_science.md'
CLASSES = json.loads((HERE / 'classes.json').read_text(encoding='utf-8'))
ROW9 = REPO / 'evals/review-faults'


def load_row9(name):
    """Keep the canonical row 9 object even when its tests imported it first.

    The private alias owns a first load; the bare alias is also registered so
    row 9's own imports and its later tests receive that same object. A foreign
    occupant is refused, never replaced. Restore sys.path even on load failure.
    """
    path = ROW9 / (name + '.py')
    alias = '_rf_' + name
    existing = sys.modules.get(name) or sys.modules.get(alias)
    if existing is not None:
        if Path(existing.__file__).resolve() != path.resolve():
            raise ImportError('row 9 module name occupied: ' + name)
        sys.modules[alias] = existing
        sys.modules[name] = existing
        return existing
    previous = list(sys.path)
    try:
        sys.path.insert(0, str(ROW9))
        spec = importlib.util.spec_from_file_location(alias, str(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    except BaseException:
        sys.modules.pop(alias, None)
        sys.modules.pop(name, None)
        raise
    finally:
        sys.path[:] = previous


rf_common = load_row9('common')
rf_review_record = load_row9('review_record')
rf_oracle = load_row9('oracle')
rf_run_reviews = load_row9('run_reviews')
rf_score = load_row9('score')

# Reuse the audit and every helper as objects, never as copied implementations.
for _name, _value in vars(rf_run_reviews).items():
    if (getattr(_value, '__module__', None) == rf_run_reviews.__name__ or
            _name in ('LIMIT', 'FORBIDDEN', 'CWD_RESET')):
        globals()[_name] = _value

validate = rf_review_record.validate
row9_invalid_reasons = rf_review_record.invalid_reasons
row9_caught = rf_oracle.caught
false_alarm = rf_oracle.false_alarm
SEVERITY = rf_oracle.SEVERITY
masked_copy = rf_score.masked_copy
ratio = rf_score.ratio
format_ratio = rf_score.format_ratio
sha256 = rf_common.sha256
read_json = rf_common.read_json
write_json = rf_common.write_json
relative_path = rf_common.relative_path


def load_cases(roots):
    """Validate the sealed science interface before using private answer bytes."""
    import re
    found = {}
    for root in roots:
        root = Path(root)
        paths = list(root.glob('[PC][0-9][0-9]'))
        for group in ('plants', 'clean'):
            paths += list((root / group).glob('[PC][0-9][0-9]'))
        for path in sorted(paths):
            expected = read_json(path / 'expected.json')
            required = {'id', 'kind', 'class', 'base_project', 'base_seed',
                        'base_sha', 'seal_type', 'requirement_ids'}
            if not isinstance(expected, dict) or not required.issubset(expected):
                raise ValueError('missing answer fields')
            cid = expected['id']
            if cid != path.name or not re.fullmatch('[PC][0-9]{2}', cid) or cid in found or cid in ('P90', 'C90'):
                raise ValueError('invalid or duplicate id')
            if root.resolve() == (HERE / 'fixtures').resolve() and cid not in ('P01', 'P02', 'C01', 'C02'):
                raise ValueError('sealed id in repository')
            if expected['base_sha'] != BASE_SHA or type(expected['base_seed']) is not int:
                raise ValueError('base identity mismatch')
            if expected['seal_type'] not in ('unsealed', 'independent_context', 'external_human_seal'):
                raise ValueError('invalid seal type')
            if expected['kind'] not in ('plant', 'clean') or cid[0] != ('P' if expected['kind'] == 'plant' else 'C'):
                raise ValueError('invalid kind')
            if not isinstance(expected['requirement_ids'], list) or not all(
                    isinstance(x, str) and re.fullmatch('R-[0-9]{3}', x) for x in expected['requirement_ids']):
                raise ValueError('invalid requirements')
            if not isinstance(expected.get('mask_literals', []), list) or not all(
                    isinstance(x, str) and x for x in expected.get('mask_literals', [])):
                raise ValueError('invalid mask literals')
            if expected['kind'] == 'clean':
                if expected['class'] is not None:
                    raise ValueError('clean class must be null')
            else:
                if expected['class'] not in CLASSES or not expected.get('match_any'):
                    raise ValueError('plant class and match_any required')
                if expected.get('min_severity', 'MINOR') not in SEVERITY:
                    raise ValueError('invalid severity')
                for entry in expected['match_any']:
                    if set(entry) != {'file', 'line_start', 'line_end', 'mode'}:
                        raise ValueError('invalid match entry')
                    if not relative_path(entry['file']) or entry['mode'] not in ('file', 'file_lines'):
                        raise ValueError('invalid match path or mode')
                    if not all(type(entry[x]) is int and entry[x] > 0 for x in ('line_start', 'line_end')) or entry['line_start'] > entry['line_end']:
                        raise ValueError('invalid match interval')
                if not (path / 'plant.diff').read_bytes():
                    raise ValueError('empty plant')
            found[cid] = {'expected': expected, 'path': path,
                'expected_sha256': sha256((path / 'expected.json').read_bytes()),
                'plant_sha256': sha256((path / 'plant.diff').read_bytes())}
    if not found:
        raise ValueError('no cases')
    return found
