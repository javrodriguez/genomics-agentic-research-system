#!/usr/bin/env python3
"""The commit scan (CP2): before a take's commit, scan every file of that commit; mask what is maskable, refuse the
rest.

    scan(files, secrets, *, rules_scanner, holdout_matcher=None) -> dict          (interface 14)

INPUTS.
  files            every file of the take's commit, as (absolute path, kind), kind from KINDS. The caller builds the
                   list from the staged index after `git add` (record checks read the index); this module never
                   walks a folder.
  secrets          (kind, value) pairs, kind from SECRET_KINDS (closed; there is no holdout kind). Values are read
                   at run time by the caller (`read_login` for a login file; the account email handed in) and are
                   never written down, printed, logged or put in an exception message by this module.
  rules_scanner    a callable (paths) -> [{"path", "line", "rule"}]: gitleaks' rules on athena later, over the
                   take's record folder only; a fake in tests. Required: a scan without one refuses (NotReady).
  holdout_matcher  a callable (text) -> [(start, end)], injected at run time from aegis on the Mac (ruling C4). No
                   wording, digest or count of one is ever handed to or held by this module. Without a matcher
                   the result records "holdout": "not-checked" (the scan never passes silently; a later gate on the
                   Mac, inside aegis, before any push, clears it). With one, "checked", and every hit is refused,
                   never masked, and reported by path, line and kind only.

MASKING, NEVER DELETING. A hit of a secret's exact value in an agent-text file (MASKABLE: transcript, stream,
session) is replaced in place by its kind's fixed marker (MARKERS; the email's is scrub.NOTE, imported). Every line
other than a masked one is written back byte for byte, every line that was JSON stays valid JSON, the value is
proved gone from the written bytes, and each file's sha256 before and after is recorded. Each masked hit is one
event (`events`, which the drive step adds into agent_adapter.BOX_KEYS' outside_reach_events), and carries its
line and its byte offset within the line, so the drive step can later tell harness furniture from the agent
(FURNITURE is PENDING: an email or account field a CLI writes itself into its stream or session file would
inflate the count; measured per harness on the stub take).

REFUSED. A hit in any other kind (the ledger, the evidence, a snapshot, a blob whose name is its own sha256, the
preflight record, the proxy log, the launch record) cannot be masked and is refused, as is every rules-scanner
finding and every holdout hit. A non-empty `refused` means the caller commits nothing and stops the run for a
ruling (`passed`).

NAMED RESIDUALS (typed cases in the tests). A value split across a line break, a value present only in an escaped
form (a JSON \\uXXXX or \\/ escape), and an email in another letter case, are not found by the exact-value search;
the rules scanner may still see them.

THE INDEX. The scan masks the files on disk. The caller built the list from the staged index, so after a scan that
masked anything it must stage the files again and check that each staged blob's sha256 equals the result's
`sha256_after` before it commits; a commit of the earlier staging would carry the unmasked value (the drive and
commit step's binding, deferred there: the lane lead's call, fold 1 Q3).

Result: {"masked": [{"path", "line", "kind", "offset"}], "events": int, "refused": [{"path", "line", "kind",
"why"}], "files": [{"path", "sha256_before", "sha256_after"}], "holdout": "checked" | "not-checked"}.

No model, no network, stdlib only (plus the round's own scrub.py, for its marker).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scrub  # noqa: E402  (scrub.NOTE: the email's marker, never retyped)

KINDS = ("transcript", "stream", "session", "ledger", "evidence", "snapshot", "blob", "preflight", "proxy-log",
         "launch")
MASKABLE = ("transcript", "stream", "session")
SECRET_KINDS = ("token", "key", "email")
MARKERS = {"token": "[masked: token]", "key": "[masked: key]", "email": scrub.NOTE}
HOLDOUT_KIND, RULE_KIND = "holdout", "rule"
CHECKED, NOT_CHECKED = "checked", "not-checked"
MIN_LENGTH = {"token": 20, "key": 20, "email": 6}
RESULT_FIELDS = ("masked", "events", "refused", "files", "holdout")

# The login-file rule (interface 11; the card's Part 3 step 7): one newline-terminated line NAME=<value>, the value
# at least 20 characters with no whitespace and no double quote; mode 600, owned by the reader, outside every git
# repository. run_take.read_login (lane w4b) holds the same rule; the merge binds the two on one fixture set.
_LOGIN_LINE = re.compile(rb"([A-Z_][A-Z0-9_]*)=([^\s\"]{20,})\n")
_NAME = re.compile(r"[A-Z_][A-Z0-9_]*")

# ------------------------------------------------------------------------------------------------- PENDING values
PENDING = "PENDING"
RULES_SCANNER = PENDING
FURNITURE = PENDING
_PENDING_WHY = {
    "rules_scanner": "the real rules scanner: gitleaks' rules on athena, over the take's record folder only (never "
                     "the Brain root); its adapter and pinned version are measured there",
    "furniture": "per-harness positions of the fields a CLI writes itself into its stream or session file (an "
                 "email, an account id), so the drive step can separate furniture from the agent's hits; measured "
                 "per harness on the stub take (W4BR-w4c-10)",
}


class NotReady(RuntimeError):
    """A real use while a value only the real box can tell is still PENDING."""


class ScanError(ValueError):
    """The scan's inputs or a file are not what it can scan. Its message never carries a secret's value."""


class LoginError(ValueError):
    """A login file that breaks the rule. Its message never carries anything read from inside the file."""


def pending() -> dict:
    return {f: why for f, why in _PENDING_WHY.items() if globals()[f.upper()] == PENDING}


def real_rules_scanner():
    """The real rules scanner's adapter: refused while it is PENDING."""
    if RULES_SCANNER == PENDING:
        raise NotReady("the real rules scanner is PENDING (gitleaks on athena)")
    return RULES_SCANNER


def furniture_positions(harness: str):
    """Where `harness` writes its own account fields: refused while FURNITURE is PENDING."""
    if FURNITURE == PENDING:
        raise NotReady("the per-harness furniture positions are PENDING (measured on the stub take)")
    return FURNITURE[harness]


# ------------------------------------------------------------------------------------------------- login files
def _in_git_repository(path: str) -> bool:
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.lexists(os.path.join(d, ".git")):
            return True
        up = os.path.dirname(d)
        if up == d:
            return False
        d = up


def read_login(path: str, name: str) -> str:
    """The value of a login file `NAME=<value>`, read at run time and never written down. Refused (LoginError, whose
    message names the rule broken and never the content) unless the file keeps the rule."""
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise LoginError("the variable name is upper-case letters, digits and underscores")
    try:
        st = os.lstat(path)
    except OSError:
        raise LoginError("the login file cannot be found") from None
    if not stat.S_ISREG(st.st_mode):
        raise LoginError("the login file is not a plain file (a link or a special file is refused)")
    if stat.S_IMODE(st.st_mode) != 0o600:
        raise LoginError("the login file's mode is not 600")
    if st.st_uid != os.geteuid():
        raise LoginError("the login file is not owned by its reader")
    if _in_git_repository(path):
        raise LoginError("the login file sits inside a git repository")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise LoginError("the login file cannot be opened") from None
    try:
        data = os.read(fd, (1 << 16) + 1)
    finally:
        os.close(fd)
    m = _LOGIN_LINE.fullmatch(data) if len(data) <= 1 << 16 else None
    if not m or m.group(1).decode() != name:
        raise LoginError("the login file is not exactly one line NAME=<at least 20 characters, no whitespace, no "
                         "double quote>")
    try:
        return m.group(2).decode("utf-8")
    except UnicodeDecodeError:
        raise LoginError("the login file's value is not UTF-8") from None


# ------------------------------------------------------------------------------------------------- the scan
def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _check_inputs(files, secrets):
    seen = set()
    for item in files:
        if not (isinstance(item, tuple) and len(item) == 2):
            raise ScanError("files are (path, kind) pairs")
        path, kind = item
        if kind not in KINDS:
            raise ScanError(f"a file's kind is one of {KINDS}")
        if not isinstance(path, str) or not os.path.isabs(path) or path in seen:
            raise ScanError("each file is a distinct absolute path")
        seen.add(path)
        try:
            st = os.lstat(path)
        except OSError:
            raise ScanError(f"{path}: not found") from None
        if not stat.S_ISREG(st.st_mode):
            raise ScanError(f"{path}: not a plain file (a link is never scanned through)")
    for item in secrets:
        if not (isinstance(item, tuple) and len(item) == 2) or item[0] not in SECRET_KINDS:
            raise ScanError(f"secrets are (kind, value) pairs, kind one of {SECRET_KINDS}")
        kind, value = item
        if not isinstance(value, str) or len(value) < MIN_LENGTH[kind] or "\n" in value or "\r" in value:
            raise ScanError(f"a {kind} value is a single-line string of at least {MIN_LENGTH[kind]} characters")


def _needles(secrets) -> list:
    """(bytes, kind), longest first, so a value inside a longer one is masked as the longer one's kind."""
    out = {}
    for kind, value in secrets:
        out.setdefault(value.encode("utf-8"), kind)
    return sorted(out.items(), key=lambda kv: -len(kv[0]))


def _spans(line: bytes, needles) -> list:
    """Non-overlapping (start, end, kind) of every needle in the line, longest needle first."""
    taken = []
    for needle, kind in needles:
        i = line.find(needle)
        while i != -1:
            j = i + len(needle)
            if not any(i < e and s < j for s, e, _ in taken):
                taken.append((i, j, kind))
            i = line.find(needle, i + 1)
    return sorted(taken)


def _mask(line: bytes, spans) -> bytes:
    out, at = [], 0
    for s, e, kind in spans:
        out += [line[at:s], MARKERS[kind].encode("utf-8")]
        at = e
    out.append(line[at:])
    return b"".join(out)


def _is_json(b: bytes) -> bool:
    try:
        json.loads(b)
        return True
    except ValueError:
        return False


def _lines(data: bytes) -> list:
    """Split on the newline only (never str.splitlines), keeping each line's own ending."""
    parts = data.split(b"\n")
    lines = [p + b"\n" for p in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def _scan_file(path, kind, data, needles):
    """(new bytes or None, masked entries, refused entries) for one file."""
    masked, refused, out, changed = [], [], [], False
    for n, line in enumerate(_lines(data), 1):
        body = line[:-1] if line.endswith(b"\n") else line
        spans = _spans(body, needles)
        if not spans:
            out.append(line)
            continue
        if kind not in MASKABLE:
            refused += [{"path": path, "line": n, "kind": k,
                         "why": f"a {k} value in a {kind} file, which cannot be masked"} for _, _, k in spans]
            out.append(line)
            continue
        new = _mask(body, spans)
        if _is_json(body) and not _is_json(new):
            refused.append({"path": path, "line": n, "kind": spans[0][2],
                            "why": "masking would leave a JSON line invalid"})
            out.append(line)
            continue
        masked += [{"path": path, "line": n, "kind": k, "offset": s} for s, _, k in spans]
        out.append(new + line[len(body):])
        changed = True
    return (b"".join(out) if changed else None), masked, refused


def _rules(scanner, paths) -> list:
    """Every rules-scanner finding, refused."""
    out = []
    for f in scanner(list(paths)):
        if not (isinstance(f, dict) and set(f) == {"path", "line", "rule"}):
            raise ScanError("a rules-scanner finding is {path, line, rule}")
        out.append({"path": f["path"], "line": f["line"], "kind": RULE_KIND,
                    "why": f"the rules scanner's rule {f['rule']!r}"})
    return out


def _holdout(holdout_matcher, path, data) -> list:
    """Every holdout hit, refused, by path, line and kind only: never the matched text, a digest or a count."""
    text = data.decode("utf-8", "surrogateescape")
    out = []
    for hit in holdout_matcher(text):
        if not (isinstance(hit, tuple) and len(hit) == 2 and all(isinstance(x, int) for x in hit)
                and 0 <= hit[0] < hit[1] <= len(text)):
            raise ScanError("the holdout matcher returns (start, end) pairs within the text")
        out.append({"path": path, "line": text.count("\n", 0, hit[0]) + 1, "kind": HOLDOUT_KIND,
                    "why": "a holdout wording matched; refused, never masked"})
    return out


def _write(path: str, data: bytes):
    with open(path, "r+b") as fh:
        fh.write(data)
        fh.truncate()
        fh.flush()
        os.fsync(fh.fileno())


def scan(files, secrets, *, rules_scanner, holdout_matcher=None) -> dict:
    """Scan every file of a take's commit (see the module docstring)."""
    if rules_scanner is None:
        raise NotReady("a real scan needs its rules scanner (gitleaks on athena: PENDING); none was given")
    files, secrets = list(files), list(secrets)
    _check_inputs(files, secrets)
    needles = _needles(secrets)
    masked, refused, records = [], [], []
    for path, kind in files:
        with open(path, "rb") as fh:
            before = fh.read()
        new, m, r = _scan_file(path, kind, before, needles)
        after = before if new is None else new
        if new is not None:
            if any(n in after for n, _ in needles):
                raise ScanError(f"{path}: a value survived its masking; nothing written")
            if [ln for ln in _lines(before) if not _spans(ln, needles)] != \
                    [ln for ln, old in zip(_lines(after), _lines(before)) if not _spans(old, needles)]:
                raise ScanError(f"{path}: masking changed a line it should not touch; nothing written")
            _write(path, after)
        masked += m
        refused += r
        if holdout_matcher is not None:
            refused += _holdout(holdout_matcher, path, after)
        records.append({"path": path, "sha256_before": _sha(before), "sha256_after": _sha(after)})
    refused += _rules(rules_scanner, [p for p, _ in files])
    return {"masked": masked, "events": len(masked), "refused": refused, "files": records,
            "holdout": NOT_CHECKED if holdout_matcher is None else CHECKED}


def passed(result: dict) -> bool:
    """May the caller commit? Only with nothing refused. A "not-checked" holdout record does not refuse here; it
    is cleared by the later gate inside aegis, before any push."""
    return not result["refused"]
