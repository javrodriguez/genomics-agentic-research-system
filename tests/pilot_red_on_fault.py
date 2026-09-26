#!/usr/bin/env python3
"""Row 13 step A red-on-fault driver (decision 0140). Not collected by the suite.

    python3 tests/pilot_red_on_fault.py

Copies the three pilot scripts, their tests, fixtures and docs/pilot into a temporary tree under
$TMPDIR, checks every module is green there, then plants each named fault on its own, runs the
module that must catch it and requires it to go red, and restores the planted file's bytes
before the next fault. The checkout is never modified.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
COPY = ('scripts/unit_economics.py', 'scripts/rerun_diff.py', 'scripts/session_turns.py',
        'tests/test_unit_economics.py', 'tests/test_rerun_diff.py',
        'tests/test_session_turns.py', 'tests/pilot_emulation.py', 'tests/fixtures/pilot',
        'docs/pilot')
MODULES = ('test_unit_economics', 'test_rerun_diff', 'test_session_turns')

# (name, file, old, new, module that must go red)
FAULTS = (
    ('a hand-typed cost accepted', 'scripts/unit_economics.py',
     'if row["cost_usd_per_sample"] != "unmetered":', 'if False:', 'test_unit_economics'),
    ('verification counted twice', 'scripts/unit_economics.py',
     'if r["stage"] == stage and r["action"] not in verification), Decimal(0))',
     'if r["stage"] == stage), Decimal(0))', 'test_unit_economics'),
    ('margin computed with no price', 'scripts/unit_economics.py',
     'add("margin", "margin", "uncomputable: no price (R-193)")',
     'add("margin", "margin", "$%s" % two(Decimal(0) - dollars))', 'test_unit_economics'),
    ('a gene id printed by rerun_diff', 'scripts/rerun_diff.py',
     '"genes matched: %d" % len(matched),',
     '"genes matched: %d (%s)" % (len(matched), matched[0] if matched else ""),',
     'test_rerun_diff'),
    ('a tool_result record counted as a human turn', 'scripts/session_turns.py',
     '    if all(results):\n        return "tool_result"',
     '    if all(results):\n        return "human"', 'test_session_turns'),
    ('a discrepancy auto-corrected', 'scripts/unit_economics.py',
     'turns, inside, outside, outside_minutes = session',
     'turns, inside, outside, outside_minutes = session[0], session[0], 0, "0.00"',
     'test_unit_economics'),
    ('a record silently skipped', 'scripts/session_turns.py',
     'raise ue.Refused("unclassifiable record line %d" % number)', 'continue',
     'test_session_turns'),
    ('a non-deterministic ordering', 'scripts/unit_economics.py',
     'stages = [s for s in vocab["stage"]\n              if any(r["stage"] == s for r in rows) or s in base]',
     'stages = list({r["stage"] for r in rows} | set(base))', 'test_unit_economics'),
    # Review round 2 (0140's addendum): one fault per new guard.
    ('a malformed quantity line ignored', 'scripts/unit_economics.py',
     'raise Refused("quantity_malformed")', 'pass', 'test_unit_economics'),
    ('an unmeasured backend called unmetered', 'scripts/unit_economics.py',
     '(("unmetered", metered), ("unmeasured", unmeasured))',
     '(("unmetered", metered + unmeasured),)', 'test_unit_economics'),
    ('uncovered stages subtracted from time saved', 'scripts/unit_economics.py',
     'two(covered_minutes / 60), two(base_total - covered_minutes / 60)',
     'two(human_minutes / 60), two(base_total - human_minutes / 60)', 'test_unit_economics'),
    ('a harness record counted as a human turn', 'scripts/session_turns.py',
     'return "harness"', 'return "human"', 'test_session_turns'),
    ('a harness record starting an attention interval', 'scripts/session_turns.py',
     'earlier = [x for x in predecessors if x < t]',
     'earlier = [x for _, x in records if x < t]',
     'test_session_turns'),
    ('a repeated run compared twice', 'scripts/rerun_diff.py',
     'raise Refused("comparison_run_duplicate")', 'pass', 'test_rerun_diff'),
    ('a parser crash left as a traceback', 'scripts/rerun_diff.py',
     'except csv.Error:\n        raise Refused("table_malformed")',
     'except KeyError:\n        raise Refused("table_malformed")', 'test_rerun_diff'),
    # Review round 3 (0140's second addendum): the lane's Python 3.13 finding, r1, r2/L6, n2.
    ('a NUL byte left to the csv module (unit_economics)', 'scripts/unit_economics.py',
     'if "\\x00" in text:\n        raise Refused(code)', 'if False:\n        raise Refused(code)',
     'test_unit_economics'),
    ('a NUL byte left to the csv module (rerun_diff)', 'scripts/rerun_diff.py',
     'if "\\x00" in text:', 'if False:', 'test_rerun_diff'),
    ('a long count read through int()', 'scripts/unit_economics.py',
     'keep("samples_in_design", canonical_decimal(m.group(1)))',
     'keep("samples_in_design", str(int(m.group(1))))', 'test_unit_economics'),
    ('a long transcript integer read through int()', 'scripts/session_turns.py',
     'json.loads(line, parse_int=Decimal)', 'json.loads(line)', 'test_session_turns'),
    ('a long comparison integer read through int()', 'scripts/rerun_diff.py',
     'parse_int=Decimal)', 'parse_int=lambda text: Decimal(int(text)))', 'test_rerun_diff'),
    ('a file read in the locale encoding', 'scripts/unit_economics.py',
     'return Path(path).read_text(encoding="utf-8")', 'return Path(path).read_text()',
     'test_unit_economics'),
    ('an out-of-range number left as a traceback', 'scripts/unit_economics.py',
     'except DecimalException:\n        # A number', 'except ZeroDivisionError:\n        # A number',
     'test_unit_economics'),
    ('a subagent reply starting an attention interval', 'scripts/session_turns.py',
     'if sidechain or compact:\n        # rulings L2 and L6',
     'if (sidechain and kind != "assistant") or compact:\n        # rulings L2 and L6',
     'test_session_turns'),
    ('a mistyped quantity keyword ignored', 'scripts/unit_economics.py',
     'QUANTITY_PREFIX = re.compile(r"^\\s*quantity\\b", re.I)',
     'QUANTITY_PREFIX = re.compile(r"quantity ")', 'test_unit_economics'),
    # Review round 4 (0140's third addendum): L7, m1, m2, n3.
    ('an unknown type classified by its flags', 'scripts/session_turns.py',
     'if not isinstance(record, dict) or record.get("type") not in KNOWN_TYPES:',
     'if not isinstance(record, dict) or (record.get("type") not in KNOWN_TYPES\n'
     '            and not record.get("isSidechain")):', 'test_session_turns'),
    ('a record outside the window used as a predecessor', 'scripts/session_turns.py',
     'within = [(kind, t) for kind, t in records if start is not None and start <= t <= end]',
     'within = list(records)', 'test_session_turns'),
    ('wall minutes spanning every record', 'scripts/session_turns.py',
     'minutes(end - start if main_thread else 0)',
     'minutes(max(t for _, t in records) - min(t for _, t in records))', 'test_session_turns'),
    ('an inverted window accepted', 'scripts/session_turns.py',
     'if main_thread and main_thread[0] > main_thread[-1]:', 'if False:', 'test_session_turns'),
    ('a meta record starting an attention interval', 'scripts/session_turns.py',
     'predecessors = [t for kind, t in within if kind in MAIN_THREAD]',
     'predecessors = [t for kind, t in within if kind != "harness"]', 'test_session_turns'),
    ('a decimal Overflow left as a traceback', 'scripts/unit_economics.py',
     'except DecimalException:\n        # A number',
     'except __import__("decimal").InvalidOperation:\n        # A number', 'test_unit_economics'),
    ('a comparison read in the locale encoding', 'scripts/rerun_diff.py',
     'comparison_path.read_text(encoding="utf-8")', 'comparison_path.read_text()',
     'test_rerun_diff'),
    ('a transcript read in the locale encoding', 'scripts/session_turns.py',
     'Path(transcript).read_text(encoding="utf-8")', 'Path(transcript).read_text()',
     'test_session_turns'),
)


def run(tree, module):
    result = subprocess.run([sys.executable, str(tree / 'tests' / (module + '.py'))],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, env=dict(os.environ))
    failed = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+)', result.stderr, re.M)))
    summary = [l for l in result.stderr.splitlines() if l.startswith(('OK', 'FAILED'))]
    return result.returncode, failed, summary[-1] if summary else 'no summary'


def main():
    red = 0
    with tempfile.TemporaryDirectory(prefix='row13-faults-') as temp:
        tree = Path(temp)
        for relative in COPY:
            source, target = REPO / relative, tree / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(str(source), str(target))
            else:
                shutil.copyfile(str(source), str(target))
        for module in MODULES:
            code, failed, summary = run(tree, module)
            print('baseline %s: %s' % (module, summary))
            if code != 0:
                print('FAIL: baseline is not green')
                return 1
        for name, relative, old, new, module in FAULTS:
            path = tree / relative
            original = path.read_bytes()
            text = original.decode()
            if text.count(old) != 1:
                print('FAIL: anchor for %r found %d times' % (name, text.count(old)))
                return 1
            path.write_text(text.replace(old, new))
            code, failed, summary = run(tree, module)
            path.write_bytes(original)
            verdict = 'RED' if code != 0 else 'GREEN (fault survived)'
            red += code != 0
            print('%s: %s; %s; %s' % (name, verdict, summary, ', '.join(failed)))
        for module in MODULES:
            code, failed, summary = run(tree, module)
            print('restored %s: %s' % (module, summary))
            if code != 0:
                return 1
    print('red-on-fault: %d/%d RED' % (red, len(FAULTS)))
    return 0 if red == len(FAULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
