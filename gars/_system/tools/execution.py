"""Shared R-073/R-075 checks; no workflow or lifecycle behavior lives here."""
import hashlib
import json
import re
import shlex
from pathlib import Path

CHARSET = r'^[A-Za-z0-9_./:@-]+$'


def shell_value(value, field):
    value = str(value)
    if not re.fullmatch(CHARSET, value):
        raise ValueError('R-075 %s must match %s (spec §7.4)' % (field, CHARSET))
    return shlex.quote(value)


def config_holds(project, substage, assay):
    """Re-hash the current assay config; absence is a refusal, not a fresh baseline."""
    path = Path(project) / '_config' / (assay + '.yaml')
    manifest = Path(substage) / 'reproducibility/manifest.json'
    try:
        expected = json.loads(manifest.read_text(encoding='utf-8'))['config_sha256']
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, ValueError, KeyError, TypeError):
        return 'R-073: config or manifest config_sha256 missing/unreadable; run prepare'
    if expected != actual:
        return 'R-073: config_sha256 changed after prepare; run prepare before collect/submit'
    return None
