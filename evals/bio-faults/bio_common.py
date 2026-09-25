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
