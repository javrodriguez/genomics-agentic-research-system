"""Row 13 step A: emulate both sides of the Python-version splits the pilot scripts must not show.

Not a test module. Two behaviours changed under the scripts between Python 3.6 and 3.13, and the
lane's Linux host (3.13) and the producer's machine (3.8.2) sat on opposite sides of both:

- `csv` raises `csv.Error` on a NUL byte through 3.10, and reads it as data from 3.11;
- `int()` of a long digit string (and so `json.loads` of a long integer) is unlimited through
  3.10 and in unpatched 3.8/3.9/3.10 releases, and raises `ValueError` past 4300 digits (a
  limit that may be lowered to 640) from 3.11 and in the 3.8.14/3.9.14/3.10.7 backports.

`emulating(side, modules)` puts the running interpreter on either side of both splits for the
duration of a `with` block, so a test can require the same refusal code on both sides whatever
Python runs it. The `new` side is emulated at the strictest allowed limit, 640 digits; the digit
limit on `int()` is emulated in the named script modules only, so no library code sees it.
"""
import contextlib
import csv
import io
import json
import re
import sys
from unittest import mock

LIMIT = 640
LONG_INTEGER = re.compile(r'(?<![0-9.eE+-])-?[0-9]{%d,}(?![0-9.eE])' % (LIMIT + 1))
PLACEHOLDER = '\ue000'  # a private-use character standing in for NUL inside the real reader

_reader, _loads, _int = csv.reader, json.loads, int


class _NulReader(object):
    """csv.reader as 3.11 and later behave: a NUL byte is data. With `raising`, as 3.10 and
    earlier behave: reading the row that holds a NUL byte raises csv.Error (at iteration, not at
    construction, like the real reader)."""

    def __init__(self, lines, *args, **kwargs):
        text = ''.join(lines).replace('\x00', PLACEHOLDER)
        self._inner = _reader(io.StringIO(text), *args, **kwargs)
        self._raising = False

    def __iter__(self):
        return self

    def __next__(self):
        row = next(self._inner)
        if self._raising and any(PLACEHOLDER in field for field in row):
            raise csv.Error('line contains NUL')
        return [field.replace(PLACEHOLDER, '\x00') for field in row]

    @property
    def line_num(self):
        return self._inner.line_num

    @property
    def dialect(self):
        return self._inner.dialect


def _raising_reader(lines, *args, **kwargs):
    reader = _NulReader(lines, *args, **kwargs)
    reader._raising = True
    return reader


class _IntType(type):
    """isinstance and issubclass against the emulated int answer as for the real int."""

    def __instancecheck__(cls, obj):
        return isinstance(obj, _int)

    def __subclasscheck__(cls, sub):
        return issubclass(sub, _int)


class _LimitedInt(metaclass=_IntType):
    """int() as 3.11 and later behave at the strictest limit: a long digit string is refused."""

    def __new__(cls, value=0, *args, **kwargs):
        if isinstance(value, (str, bytes)):
            digits = value.strip().lstrip(b'-+' if isinstance(value, bytes) else '-+')
            if len(digits) > LIMIT:
                raise ValueError('Exceeds the limit (%d digits) for integer string conversion'
                                 % LIMIT)
        return _int(value, *args, **kwargs)


def _limited_loads(text, *args, **kwargs):
    if kwargs.get('parse_int') in (None, int) and isinstance(text, str) and \
            LONG_INTEGER.search(text):
        raise ValueError('Exceeds the limit (%d digits) for integer string conversion' % LIMIT)
    return _loads(text, *args, **kwargs)


@contextlib.contextmanager
def emulating(side, modules=()):
    """`old` (3.10 and earlier, no digit limit) or `new` (3.11 and later, the strictest limit)."""
    assert side in ('old', 'new'), side
    setter = getattr(sys, 'set_int_max_str_digits', None)
    before = sys.get_int_max_str_digits() if setter else None
    with contextlib.ExitStack() as stack:
        if side == 'old':
            stack.enter_context(mock.patch.object(csv, 'reader', _raising_reader))
            if setter:
                setter(0)
        else:
            stack.enter_context(mock.patch.object(csv, 'reader', _NulReader))
            stack.enter_context(mock.patch.object(json, 'loads', _limited_loads))
            for module in modules:
                stack.enter_context(mock.patch.object(module, 'int', _LimitedInt, create=True))
            if setter:
                setter(LIMIT)
        try:
            yield
        finally:
            if setter:
                setter(before)


def outcome(main, argv):
    """(exit code, stdout, stderr) of a script's main() run in this process."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()
