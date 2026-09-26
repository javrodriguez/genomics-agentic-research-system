#!/usr/bin/env python3
"""R-165 audit (row 14): every _system/ commit on the first-parent line since activation.

  python3 gars/_system/hooks/audit_trailers.py [--rev <commit>]      (default HEAD)

Loads the protected pre-push hook with runpy and calls its own validate_evidence for every
checked commit, with the committed-evidence snapshot at the given commit and the predecessor
named by the hook's previous_bench helper. CI runs it on every push; the hook is not armed in
every push path, so this is the enforcement of record. Exit 1 on any refusal, and when an
activation exists but nothing was checked (a zero-graded audit is a failure, never a pass).
"""
import argparse
from pathlib import Path
import runpy
import subprocess
import sys


def refusing(error):
    def read_record(name):
        raise error
    return read_record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--rev', default='HEAD')
    args = parser.parse_args(argv)
    hook = runpy.run_path(str(Path(__file__).resolve().with_name('pre-push')))
    git = hook['git_bytes']
    try:
        root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'],
                                       stderr=subprocess.PIPE).decode().strip()
        if git(root, 'rev-parse', '--is-shallow-repository').strip() != b'false':
            print('trailers audit: REFUSED (shallow history cannot establish trailer activation)')
            return 1
        given = git(root, 'rev-parse', '--verify', args.rev + '^{commit}').decode('ascii').strip()
        activation = hook['activation_of'](root, given)
        if activation is None:
            print('trailers audit: not applicable — not activated at %s; graded 0 commits and '
                  'claims nothing' % given[:7])
            return 0
        chain = hook['first_parent_chain'](root, given)
        walk = list(reversed(chain[:chain.index(activation) + 1]))
        checked = [commit for commit in walk if hook['touches_system'](root, commit)]
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as error:
        reason = str(error) if isinstance(error, ValueError) else 'cannot read history'
        print('trailers audit: REFUSED (%s)' % reason)
        return 1
    verified = 0
    for commit in checked:
        try:
            expect_previous = hook['previous_bench'](root, commit)
            try:
                reader = hook['committed_reader'](root, commit, given)
            except ValueError as error:
                # Reported after the trailers are read, so a commit without them is named as such.
                reader = refusing(error)
            hook['validate_evidence'](root, commit, reader, expect_previous)
            verified += 1
            print('  verified %s (Bench previous: %s)' % (commit, expect_previous or 'none'))
        except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as error:
            reason = str(error) if isinstance(error, ValueError) else 'cannot read trailer evidence/history'
            print('  REFUSED %s (%s)' % (commit, reason))
    print('trailers audit: %d/%d _system first-parent commits since activation %s verified; '
          'graded %d of %d seen' % (verified, len(checked), activation[:7], len(checked), len(checked)))
    if not checked:
        print('trailers audit: FAIL activation exists and 0 commits were checked; the walk is broken')
        return 1
    return 0 if verified == len(checked) else 1


if __name__ == '__main__':
    sys.exit(main())
