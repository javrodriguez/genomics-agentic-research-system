#!/usr/bin/env python3
"""Run one registered typed call: tool_call.py <tool> <json-args> (R-092)."""
import json
import subprocess
import sys
from tools.policy import (WORKSPACE, Refusal, named, authorize, argv_for,
                          launch_role, validate)


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
        proc = subprocess.run(argv_for(tool, args), cwd=str(WORKSPACE),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=tool['timeout_seconds'])
        result = {'exit_code':proc.returncode,
                  'stdout':proc.stdout.decode('utf-8', 'replace'),
                  'stderr':proc.stderr.decode('utf-8', 'replace')}
        validate(result, tool['output_schema'], 'output')
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
