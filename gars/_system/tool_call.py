#!/usr/bin/env python3
"""Run one registered typed call: tool_call.py <tool> <json-args> (R-092).

On a non-public project the call is judged and filtered by `tools/closed_output.py`
(decision 0141): a path outside the workspace, or outside the one closed project a call names,
is refused before running, as is a DE door's design or counts anywhere but its fixed layout,
and the output keeps only the tool's keep-list."""
import json
import os
import subprocess
import sys
from tools.policy import (WORKSPACE, Refusal, named, authorize, argv_for,
                          launch_role, validate)
from tools.closed_output import (ClosedRefusal, call_strings, closed, filter_output,
                                 fixed_inputs, registration)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if len(argv) != 2:
            raise Refusal('args', 'expected tool name and JSON arguments')
        tool = named(argv[0])
        try:
            args = json.loads(argv[1])
        except ValueError:
            raise Refusal('args', 'could not read JSON arguments')
        authorize(tool, args, launch_role())
        try:
            project = None if registration(tool, args, WORKSPACE, os.getcwd()) else \
                closed(call_strings(args), WORKSPACE, os.getcwd())
            if project is not None:
                fixed_inputs(tool['name'], args, WORKSPACE, project)
        except ClosedRefusal as exc:
            if exc.code == 'path_not_fixed_layout':
                raise Refusal('args', exc.code + ': on a non-public project this door reads its '
                              'design and counts only at their fixed, machine-written paths '
                              '(decision 0141)', 'R-094')
            raise Refusal('args', exc.code + ': a non-public project exists, so a call may name '
                          'only paths inside the workspace and inside the one closed project it '
                          'names (decision 0141)', 'R-094')
        proc = subprocess.run(argv_for(tool, args), cwd=str(WORKSPACE),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=tool['timeout_seconds'])
        result = {'exit_code':proc.returncode,
                  'stdout':proc.stdout.decode('utf-8', 'replace'),
                  'stderr':proc.stderr.decode('utf-8', 'replace')}
        validate(result, tool['output_schema'], 'output')
        if project is not None:
            result['stdout'], result['stderr'] = filter_output(
                tool['name'], result['stdout'], result['stderr'], proc.returncode)
        print(json.dumps(result, sort_keys=True))
        return proc.returncode
    except Refusal as exc:
        print(json.dumps(exc.record(), sort_keys=True))
        return 2
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps(Refusal('execution', type(exc).__name__).record(), sort_keys=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
