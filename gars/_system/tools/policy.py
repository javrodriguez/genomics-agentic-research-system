"""Fail-closed typed argument and role policy (R-092/R-093; decision 0058)."""
import json
import os
import re
import shlex
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
REGISTRY = Path(__file__).with_name('registry.json')
# GNU find and bfs (the agent's Bash find) start the expression at these words as well as at
# a '-'-led one; as a path, each would leave find walking its default '.'.
FIND_OPERATORS = ('!', '(', ')', ',')


class Refusal(ValueError):
    def __init__(self, field, message, rule='R-092', alternative=None):
        self.field, self.rule = field, rule
        self.alternative = alternative
        super().__init__(message)

    def record(self):
        return {'type': 'tool_refusal', 'field': self.field, 'rule': self.rule,
                'message': str(self), 'source': 'spec §9.1–§9.6; decision 0058',
                'alternative': self.alternative}


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))['tools']


def usage(tool):
    """Render the existing registry entry; this is advice, never a parser."""
    if tool is None:
        return 'supply the required fields declared by the tool schema.'
    if tool.get('filesystem'):
        props = tool['input_schema']['properties']
        flags = props['flags']['items']['enum']
        return 'usage: ' + tool['argv'][0] + (' [' + ' '.join(flags) + ']' if flags else '') + (
            ' PATTERN' if 'pattern' in props else '') + ' PATH.'
    words = list(tool['argv'])
    for key, spec in tool['cli'].items():
        arg = (spec['flag'] + ' ' if spec['flag'] else '')
        if tool['input_schema']['properties'][key]['type'] != 'boolean':
            arg += '<' + key + '>'
        words.append(arg.strip() if key in tool['input_schema'].get('required', [])
                     else '[' + arg.strip() + ']')
    return ('submit a typed call through python3 _system/tool_call.py ' + tool['name'] +
            " '<json>'; usage of its arguments: " + ' '.join(words) + '.')


def allowed_calls():
    tools = registry()
    return ('Next: use a file command (' + ' '.join(t['argv'][0] for t in tools
            if t.get('filesystem')) + "), or a typed call, python3 _system/tool_call.py <tool> '<json>', "
            'for a tool named in _system/tools/registry.json.')


def literal_next():
    tools = registry()
    return ('Next: one command per call: run each step as its own call; quote literal #, braces, '
            'tildes, parentheses, *, ? or [ in arguments, and quote literal ; | & < > only in arguments '
            'of file tools (' + ' '.join(t['argv'][0] for t in tools if t.get('filesystem')) + ').')


def validate(value, schema, field='args', tool=None):
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}
    if kind not in types or not isinstance(value, types[kind]) or (kind == 'integer' and isinstance(value, bool)):
        raise Refusal(field, 'expected ' + str(kind) + ' (R-092; decision 0058).', alternative='Next: supply a JSON ' + str(kind) + ' for ' + field + '.')
    if 'enum' in schema and value not in schema['enum']:
        raise Refusal(field, 'value is outside the declared vocabulary; allowed values: ' + (', '.join(str(v) for v in schema['enum']) or 'none') + ' (R-092; decision 0058).', alternative='Next: choose a listed value for ' + field + '; omit this optional field or flag if no values are listed.')
    if kind == 'object':
        for key in schema.get('required', []):
            if key not in value:
                raise Refusal(field + '.' + key, 'required field is missing (R-092; decision 0058).', alternative='Next: supply ' + key + '; ' + usage(tool))
        for key, item in value.items():
            if key not in schema.get('properties', {}):
                raise Refusal(field + '.' + key, 'undeclared field (R-092; decision 0058).', alternative='Next: remove ' + key + '; allowed fields: ' + ', '.join(schema.get('properties', {})) + '.')
            validate(item, schema['properties'][key], field + '.' + key, tool)
    elif kind == 'array':
        if len(value) < schema.get('minItems', 0):
            raise Refusal(field, 'too few items (R-092; decision 0058).', alternative='Next: supply at least %s items for %s.' % (schema.get('minItems', 0), field))
        for i, item in enumerate(value):
            validate(item, schema['items'], '%s[%d]' % (field, i), tool)
    elif kind == 'string':
        if len(value) < schema.get('minLength', 0) or '\x00' in value:
            raise Refusal(field, 'empty or NUL-containing value (R-092; decision 0058).', alternative='Next: supply a nonempty value without NUL bytes for ' + field + '.')
        if 'pattern' in schema and not re.fullmatch(schema['pattern'], value):
            raise Refusal(field, 'value does not match ' + schema['pattern'] + ' (R-092; decision 0058).', alternative='Next: supply ' + field + ' in the format ' + schema['pattern'] + '.')


def launch_role():
    """Default producer. No CLI flag, payload member or environment role override.

    Agent entry points stay producer-only. The human approval CLI captures its OS
    identity separately (0059); reviewer OS-user deployment remains NOT met.
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
    validate(args, tool['input_schema'], tool=tool)
    cwd = Path(cwd or root)
    # Project-writing helpers cannot redirect their output into template code or outside
    # the workspace through --project, traversal, or an existing symlink.
    for key in ('project', 'workspace'):
        if key in args:
            p = cwd / args[key]
            if not within(p, Path(root) / 'projects') or p.resolve() == (Path(root) / 'projects').resolve():
                raise Refusal('args.' + key, 'must resolve to a project under projects/ (R-094; decision 0058).', 'R-094', alternative='Next: pass --project projects/<name> for an existing project (or --workspace projects/<name> when this tool uses --workspace).')
    for key in ('script', 'h5ad', 'counts', 'design'):
        if key in args and args[key].startswith('-'):
            raise Refusal('args.' + key, 'an operand cannot be an option (R-092; decision 0058).', alternative='Next: pass a workspace-relative file path, prefixed with ./ if its name starts with a dash; ' + usage(tool))
    if tool.get('filesystem'):
        for p in args['paths']:
            if not within(cwd / p, root):
                raise Refusal('args.paths', '%s is outside the workspace (%s); a session reads only inside it (R-073 (recorded as R-094)).' % (p, root), 'R-094', alternative="Next: if it is a command's background output, run that command in the foreground and read its result directly (decision 0160).")
            if p.startswith('-') or p in ('-',) or '\n' in p:
                raise Refusal('args.paths', 'paths cannot be options or stdin (R-092; decision 0058).', alternative='Next: pass a workspace-relative file path without line breaks, prefixed with ./ if its name starts with a dash.')
        if tool['name'] == 'fs.find' and any(p in FIND_OPERATORS for p in args['paths']):
            raise Refusal('args.paths', 'find reads a lone !, (, ) or , as an operator, not a '
                          'path (R-092; decision 0185).',
                          alternative='Next: name the folder first, as in find . -name x.')
        if tool['name'] == 'fs.find' and len(args['paths']) != 1:
            raise Refusal('args.paths', 'find accepts one path and only the declared predicates (R-092; decision 0185).',
                          alternative='Next: run find once per workspace folder, as in find . -name x.')
        # Each predicate takes exactly one value, which must fullmatch its declared pattern.
        predicates = tool.get('predicates', {})
        expression = args.get('expression', [])
        for i in range(0, len(expression), 2):
            word = expression[i]
            if word not in predicates or i + 1 >= len(expression) \
                    or not re.fullmatch(predicates[word], expression[i + 1]):
                raise Refusal('args.expression[%d]' % i, 'find accepts only these predicates, '
                              'each with one valid value: ' + ', '.join(sorted(predicates)) +
                              ' (R-092; decision 0185).',
                              alternative='Next: choose a listed predicate and a value matching its pattern in _system/tools/registry.json, as in find . -name x.')


def authorize(tool, args, role, root=WORKSPACE, cwd=None):
    validate_args(tool, args, root, cwd)
    if tool.get('unavailable'):
        raise Refusal('tool', tool['unavailable'] + ' (R-092; decision 0058).', alternative='Next: ask the workspace maintainer to provide the unavailable tool capability before retrying.')
    decision = decide(tool, role)
    if decision != 'allow':
        raise Refusal('role', decision + ': ' + role + ' cannot invoke ' + tool['name'] + ' (R-093; decision 0058).', 'R-093', alternative='Next: ask a human authorized for ' + tool['name'] + ' to perform this action in their own terminal.')
    if tool.get('substage') and tool['name'].endswith('.collect'):
        from tools.execution import config_holds
        project = Path(cwd or root) / args['project']
        problem = config_holds(project, project / '02_bioinformatics' / tool['assay'] / tool['substage'], tool['assay'])
        if problem:
            raise Refusal('config_sha256', problem.split(';', 1)[0].replace('R-073: ', '', 1) + ' (R-073; decision 0058).', 'R-073', alternative='Next: ask the human to restore or review the configuration and run the sub-stage prepare step before collecting.')
    return decision


def named(name):
    for t in registry():
        if t['name'] == name:
            return t
    raise Refusal('tool', 'unregistered tool ' + str(name) + ' (R-092; decision 0058).', alternative=allowed_calls())


def argv_for(tool, args, root=WORKSPACE):
    if tool.get('filesystem'):
        argv = tool['argv'] + args.get('flags', [])
        if tool['name'] == 'fs.checksum' and '-a' in args.get('flags', []):
            argv += ['256']
        if 'pattern' in args:
            argv += ['--', args['pattern']]
        if 'predicates' in tool:
            return argv + args['paths'] + args.get('expression', [])
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
        raise Refusal('command', 'could not read a nonempty command (R-092; decision 0058).', alternative='Next: supply one registered command, for example ls _system.')
    # Bash treats quoted operators as literal bytes; only filesystem argv may use them.
    # $ and backticks expand even in double quotes, so refuse them everywhere, as CR/LF.
    operators = ';|&<>'
    if any(c in command for c in ('`', '$', '\n', '\r')):
        raise Refusal('command', 'dollar signs, backticks and line breaks are refused even inside quotes (R-092; decision 0165).', alternative='Next: one command per call: run each step as its own call; use literal argument values without dollar signs, backticks or line breaks.')
    quote, i, quoted_operator, glob = None, 0, False, False
    word_start = True
    while i < len(command):
        char = command[i]
        if quote is None:
            # An unquoted word-start # discards the rest in the shell, not shlex.
            if char == '#' and word_start:
                raise Refusal('command', 'an unquoted word-start # starts a shell comment (R-092; decision 0165).', alternative='Next: one command per call: run each step as its own call; quote a literal # in an argument, for example grep -n "#" CONTEXT.md.')
            word_start = char in ' \t'
            if char in ("'", '"'):
                quote = char
            elif char == '\\':
                following = command[i + 1:i + 2]
                if following and following in operators:
                    raise Refusal('command', 'an escaped unquoted operator is refused (R-092; decision 0165).', alternative=literal_next())
                i += 1
            # Unquoted braces, tildes and parentheses can carry shell syntax.
            elif char in operators + '{}~()':
                raise Refusal('command', 'unquoted operators, braces, tildes and parentheses are refused (R-092; decision 0165).', alternative=literal_next())
            elif char in '*?[':
                glob = True
        elif char == quote:
            quote = None
        elif quote == '"' and char == '\\' and command[i + 1:i + 2] in ('"', '\\'):
            i += 1
        elif char in operators:
            quoted_operator = True
        i += 1
    if quote is not None:
        raise Refusal('command', 'could not read command quoting (R-092; decision 0165).', alternative='Next: close each argument with its matching quote and submit one command.')
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        raise Refusal('command', 'could not read command quoting (R-092; decision 0165).', alternative='Next: close each argument with its matching quote and submit one command.')
    filesystem = {tool['argv'][0] for tool in registry() if tool.get('filesystem')}
    # The guard judges the unexpanded word; bash expands an unquoted glob into the operands,
    # where a planted '--pre=x' or '-delete' becomes an option and '..*' can reach '..'.
    if glob and tokens and tokens[0] in filesystem:
        raise Refusal('command', 'an unquoted *, ? or [ is expanded by the shell; the guard judges the unexpanded argument (R-092; decision 0185).',
                      alternative='Next: quote the pattern, as in grep -n "x*" FILE, or name a workspace folder first, as in find DIR -name "*.py".')
    if quoted_operator and (not tokens or tokens[0] not in filesystem):
        raise Refusal('command', 'a quoted operator is allowed only in a file tool argument (R-092; decision 0165).', alternative='Next: one command per call: run each step as its own call; send a search pattern with | directly to grep or rg, for example grep -n "a|b" FILE.')
    return tokens


def parse_argv(tokens, root=WORKSPACE, cwd=None):
    cwd = Path(cwd or root)
    if not tokens:
        raise Refusal('command', 'empty command (R-092; decision 0058).', alternative='Next: supply one registered command, for example ls _system.')
    if tokens[0] == 'python3' and len(tokens) >= 2:
        path = (cwd / tokens[1]).resolve()
        if path == (Path(root) / '_system/tool_call.py').resolve():
            if len(tokens) != 4:
                raise Refusal('args', 'dispatcher requires tool and one JSON object (R-092; decision 0058).', alternative="Next: use python3 _system/tool_call.py <tool> '<json-object>' with a registered tool and its declared arguments.")
            try:
                return named(tokens[2]), json.loads(tokens[3])
            except Refusal:
                raise Refusal('args', 'the tool name is not registered (R-092; decision 0058).', alternative=allowed_calls())
            except ValueError:
                raise Refusal('args', 'could not read JSON arguments (R-092; decision 0058).', alternative="Next: pass one valid JSON object in single quotes, for example python3 _system/tool_call.py stage00_register.assays '{}'.")
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
                        raise Refusal('args.' + flag, 'undeclared option (R-092; decision 0058).', alternative='Next: ' + usage(tool))
                    key = flags[flag]
                    if key in args:
                        raise Refusal('args.' + key, 'duplicate option (R-092; decision 0058).', alternative='Next: ' + usage(tool))
                    schema = tool['input_schema']['properties'][key]
                    if schema['type'] == 'boolean':
                        if sep: raise Refusal('args.' + key, 'boolean flag takes no value (R-092; decision 0058).', alternative='Next: ' + usage(tool))
                        args[key] = True
                    elif schema['type'] == 'array':
                        vals = [val] if sep else []
                        while i + 1 < len(rest) and not rest[i+1].startswith('--'):
                            i += 1; vals.append(rest[i])
                        args[key] = vals
                    else:
                        if not sep:
                            i += 1
                            if i >= len(rest): raise Refusal('args.' + key, 'missing value (R-092; decision 0058).', alternative='Next: ' + usage(tool))
                            val = rest[i]
                        args[key] = val
                else:
                    if not positional: raise Refusal('args', 'unexpected positional argument (R-092; decision 0058).', alternative='Next: ' + usage(tool))
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
                if not rest: raise Refusal('args.pattern', 'missing search pattern (R-092; decision 0058).', alternative='Next: ' + usage(tool))
                args['pattern'] = rest.pop(0)
            if 'predicates' in tool:
                cut = next((i for i, w in enumerate(rest)
                            if w.startswith('-') or w in FIND_OPERATORS), len(rest))
                rest, expression = rest[:cut], rest[cut:]
                if expression:
                    args['expression'] = expression
            args['paths'] = rest or ['.']
            return tool, args
    raise Refusal('command', 'this helper, interpreter or executable is not registered (R-092; decision 0058).', alternative=allowed_calls())
