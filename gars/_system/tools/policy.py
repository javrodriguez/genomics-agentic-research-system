"""Fail-closed typed argument and role policy (R-092/R-093; decision 0053)."""
import json
import os
import re
import shlex
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
REGISTRY = Path(__file__).with_name('registry.json')


class Refusal(ValueError):
    def __init__(self, field, message, rule='R-092'):
        self.field, self.rule = field, rule
        super().__init__(message)

    def record(self):
        return {'type': 'tool_refusal', 'field': self.field, 'rule': self.rule,
                'message': str(self), 'source': 'spec §9.1–§9.6; decision 0053',
                'alternative': 'python3 _system/tool_call.py fs.read '
                               '\'{"paths":["CONTEXT.md"]}\''}


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))['tools']


def validate(value, schema, field='args'):
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}
    if kind not in types or not isinstance(value, types[kind]) or (kind == 'integer' and isinstance(value, bool)):
        raise Refusal(field, 'expected ' + str(kind))
    if 'enum' in schema and value not in schema['enum']:
        raise Refusal(field, 'value is outside the declared vocabulary')
    if kind == 'object':
        for key in schema.get('required', []):
            if key not in value:
                raise Refusal(field + '.' + key, 'required field is missing')
        for key, item in value.items():
            if key not in schema.get('properties', {}):
                raise Refusal(field + '.' + key, 'undeclared field')
            validate(item, schema['properties'][key], field + '.' + key)
    elif kind == 'array':
        if len(value) < schema.get('minItems', 0):
            raise Refusal(field, 'too few items')
        for i, item in enumerate(value):
            validate(item, schema['items'], '%s[%d]' % (field, i))
    elif kind == 'string':
        if len(value) < schema.get('minLength', 0) or '\x00' in value:
            raise Refusal(field, 'empty or NUL-containing value')
        if 'pattern' in schema and not re.fullmatch(schema['pattern'], value):
            raise Refusal(field, 'value does not match ' + schema['pattern'])


def launch_role():
    """Default producer. No CLI flag, payload member or environment role override.

    Agent entry points stay producer-only. The human approval CLI captures its OS
    identity separately (0054); reviewer OS-user deployment remains NOT met.
    """
    return 'producer'


def decide(tool, role):
    return tool['roles'].get(role, 'refuse')


def within(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def validate_args(tool, args, root=WORKSPACE, cwd=None):
    validate(args, tool['input_schema'])
    cwd = Path(cwd or root)
    # Project-writing helpers cannot redirect their output into template code or outside
    # the workspace through --project, traversal, or an existing symlink.
    for key in ('project', 'workspace'):
        if key in args:
            p = cwd / args[key]
            if not within(p, Path(root) / 'projects') or p.resolve() == (Path(root) / 'projects').resolve():
                raise Refusal('args.' + key, 'must resolve to a project under projects/', 'R-094')
    for key in ('script', 'h5ad', 'counts', 'design'):
        if key in args and args[key].startswith('-'):
            raise Refusal('args.' + key, 'an operand cannot be an option')
    if tool.get('filesystem'):
        for p in args['paths']:
            if not within(cwd / p, root):
                raise Refusal('args.paths', 'R-073: filesystem reads stay inside the workspace; human approval store is protected', 'R-094')
            if p.startswith('-') or p in ('-',) or '\n' in p:
                raise Refusal('args.paths', 'paths cannot be options or stdin')
        if tool['name'] == 'fs.find' and len(args['paths']) != 1:
            raise Refusal('args.paths', 'find accepts one path and no expressions')


def authorize(tool, args, role, root=WORKSPACE, cwd=None):
    validate_args(tool, args, root, cwd)
    if tool.get('unavailable'):
        raise Refusal('tool', tool['unavailable'])
    decision = decide(tool, role)
    if decision != 'allow':
        raise Refusal('role', decision + ': ' + role + ' cannot invoke ' + tool['name'], 'R-093')
    if tool.get('substage') and tool['name'].endswith('.collect'):
        from tools.execution import config_holds
        project = Path(cwd or root) / args['project']
        problem = config_holds(project, project / '02_bioinformatics' / tool['assay'] / tool['substage'], tool['assay'])
        if problem:
            raise Refusal('config_sha256', problem, 'R-073')
    return decision


def named(name):
    for t in registry():
        if t['name'] == name:
            return t
    raise Refusal('tool', 'unregistered tool ' + str(name))


def argv_for(tool, args, root=WORKSPACE):
    if tool.get('filesystem'):
        argv = tool['argv'] + args.get('flags', [])
        if tool['name'] == 'fs.checksum' and '-a' in args.get('flags', []):
            argv += ['256']
        if 'pattern' in args:
            argv += ['--', args['pattern']]
        return argv + args['paths']
    argv = list(tool['argv'])
    argv[1] = str(Path(root) / argv[1])
    for key, spec in tool['cli'].items():
        if key not in args or args[key] is False:
            continue
        value = args[key]
        if spec['flag']:
            argv.append(spec['flag'])
        if value is not True:
            argv.extend(value if isinstance(value, list) else [str(value)])
    return argv


def simple_tokens(command):
    if not isinstance(command, str) or not command.strip():
        raise Refusal('command', 'could not read a nonempty command')
    # Shell syntax is forbidden even inside quoted arguments on the Bash transport.
    # Rich text containing it can use the JSON dispatcher through a native tool caller.
    if any(c in command for c in (';', '|', '&', '<', '>', '`', '$', '\n', '\r')):
        raise Refusal('command', 'only one simple command; no shell operators or expansion')
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        raise Refusal('command', 'could not read command quoting')


def parse_argv(tokens, root=WORKSPACE, cwd=None):
    cwd = Path(cwd or root)
    if not tokens:
        raise Refusal('command', 'empty command')
    if tokens[0] == 'python3' and len(tokens) >= 2:
        path = (cwd / tokens[1]).resolve()
        if path == (Path(root) / '_system/tool_call.py').resolve():
            if len(tokens) != 4:
                raise Refusal('args', 'dispatcher requires tool and one JSON object')
            try:
                return named(tokens[2]), json.loads(tokens[3])
            except ValueError:
                raise Refusal('args', 'could not read JSON arguments')
        for tool in registry():
            prefix = tool['argv']
            if tool.get('filesystem') or path != (Path(root) / prefix[1]).resolve():
                continue
            if len(prefix) == 3 and tokens[2:3] != prefix[2:3]:
                continue
            rest = tokens[len(prefix):]
            args = {}; positional = [k for k, s in tool['cli'].items() if s['flag'] is None]
            flags = {s['flag']:k for k,s in tool['cli'].items() if s['flag']}
            i = 0
            while i < len(rest):
                word = rest[i]
                if word.startswith('-'):
                    flag, sep, val = word.partition('=')
                    if flag not in flags:
                        raise Refusal('args.' + flag, 'undeclared option')
                    key = flags[flag]
                    if key in args:
                        raise Refusal('args.' + key, 'duplicate option')
                    schema = tool['input_schema']['properties'][key]
                    if schema['type'] == 'boolean':
                        if sep: raise Refusal('args.' + key, 'boolean flag takes no value')
                        args[key] = True
                    elif schema['type'] == 'array':
                        vals = [val] if sep else []
                        while i + 1 < len(rest) and not rest[i+1].startswith('--'):
                            i += 1; vals.append(rest[i])
                        args[key] = vals
                    else:
                        if not sep:
                            i += 1
                            if i >= len(rest): raise Refusal('args.' + key, 'missing value')
                            val = rest[i]
                        args[key] = val
                else:
                    if not positional: raise Refusal('args', 'unexpected positional argument')
                    args[positional.pop(0)] = word
                i += 1
            return tool, args
    for tool in registry():
        if tool.get('filesystem') and tokens[0] == tool['argv'][0]:
            rest = tokens[1:]; args = {'paths':[], 'flags':[]}
            if tool['name'] == 'fs.checksum' and rest[:2] == ['-a', '256']:
                args['flags'] = ['-a']; rest = rest[2:]
            while rest and rest[0].startswith('-'):
                args['flags'].append(rest.pop(0))
            if 'pattern' in tool['input_schema']['properties'] and '--files' not in args['flags']:
                if not rest: raise Refusal('args.pattern', 'missing search pattern')
                args['pattern'] = rest.pop(0)
            args['paths'] = rest or ['.']
            return tool, args
    raise Refusal('command', 'unregistered helper, interpreter or executable')
