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
  rules_scanner    a callable (paths) -> [{"path", "line", "rule"}]: the real one is rules_scanner.real_rules_scanner().build(runtime,
                   report_dir), the pinned gitleaks adapter in box/rules_scanner.py, over the
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

THE WITNESS. scan_with_witness(...) -> (the same result, {path: witness}) through the same core. Per file:
{"schema": 1, "original_sha256", "published_sha256", "original_bytes", "published_bytes", "replacements":
[{"start", "end", "kind", "replacement_id"}]}: absolute byte offsets in the original, end exclusive, nonempty,
disjoint and increasing; replacement_id fixed per kind by REPLACEMENT_IDS over the pinned MARKERS; derived only from
the masked entries (an unchanged or refused file carries an empty list); checked to rebuild the masked bytes before
the file is written. A witness never carries a secret's value, nor a digest of a value alone (its whole-file
original_sha256, like files[].sha256_before, can with the spans test a guess at a low-entropy value offline). Hashes
alone do not prove the transformation: a verifier needs the private original bytes.

No model, no network, stdlib only (plus the round's own scrub.py, for its marker).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import stat
import sys
import tempfile

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
RESULT_FIELDS = ("masked", "events", "refused", "files", "holdout", "ruled")
# The transformation witness (scan_with_witness): one fixed replacement identity per secret kind, bound to the pinned
# marker map above; a verifier maps an id back to its marker's bytes through replacement_marker, never to caller bytes.
WITNESS_SCHEMA = 1
WITNESS_FIELDS = ("schema", "original_sha256", "published_sha256", "original_bytes", "published_bytes",
                  "replacements")
REPLACEMENT_IDS = {"token": "mask-token-v1", "key": "mask-key-v1", "email": "mask-email-v1"}

# The login-file rule (interface 11; the card's Part 3 step 7): one newline-terminated line NAME=<value>, the value
# at least 20 characters with no whitespace and no double quote; mode 600, owned by the reader, outside every git
# repository. run_take.read_login (lane w4b) holds the same rule; the merge binds the two on one fixture set.
# Wave 4 merge, binding 5 (glitch-f3's ruling under Javier's delegation; a merge-time exception to this lane): the
# two readers agree on four further points. (i) ASCII only: the value excludes every byte above 0x7f and every byte
# a str regex reads as whitespace (bytes' \s plus 0x1c-0x1f). (ii) The name is one of the caller's `allowed` names
# (the caller passes run_take.LOGIN_VARIABLE's values; this module never imports run_take). (iii) At most
# LOGIN_MAX_BYTES. (iv) An absolute path only.
_LOGIN_LINE = re.compile(rb"([A-Z_][A-Z0-9_]*)=([^\s\"\x1c-\x1f\x80-\xff]{20,})\n")
_NAME = re.compile(r"[A-Z_][A-Z0-9_]*")
LOGIN_MAX_BYTES = 4096

# ------------------------------------------------------------------------------------------------- scanner rulings
# A rules-scanner finding is admitted only by an exact ruling, never by switching a rule off (the push door's style:
# the rule plus the sha256 of the exact line). OD57 (Javier's own ruling, his verified terminal reply "scan-envmd-1
# safe" at 2026-10-16T12:52:33Z, outcome "safe" on ask T83, recorded by glitch-27): gitleaks' generic-api-key flags
# line 175 of gars/_references/environment.md ("Key pinned versions: ...", a list of package versions; blob 2c0ea574,
# byte-identical on public GARS main a97fa9cd) when an agent reads that doc. The ruling binds that one line's text
# (sha256 of its 80 bytes, no newline), decoded from the JSON record, inside a tool result (a Read result, or a Bash
# grep or cat of that doc as _ruled_bash reads it; main thread or sub-agent), in an agent-text kind (MASKABLE). Any
# other rule, any other line, the same text anywhere outside a tool result, or a match the line alone does not
# explain still refuses.
RULED_LINES = (
    {"ruling": "OD57", "rule": "generic-api-key", "bytes": 80,
     "sha256": "0b85623f36eef7c6e7ca19c7900e865fd7ddbfe5853197b5c1d2e246d81df313",
     "source": "gars/_references/environment.md line 175, blob 2c0ea574434dbc4f1b9c454c8788fc68fcca2a13"},
)
# The line prefixes a tool result may put before the ruled text (allow-list): Read's and `cat -n`'s line number and
# tab (or arrow), `grep -n`'s number and colon, and grep's file name (the ruled doc only) with or without a number.
_RULED_PREFIX = re.compile(r"(?:\s*[0-9]+(?:\t|\u2192)|[0-9]+:|(?:[A-Za-z0-9_.-]*/)*environment\.md:(?:[0-9]+:)?)?")
_TOOL_RESULT_KEYS = ("toolUseResult", "tool_use_result")


# ------------------------------------------------------------------------------------------------- PENDING values
PENDING = "PENDING"
# FILLED 14 Oct 2026 (glitch-06, row 8 of the box lane's open table): the reviewed adapter box/rules_scanner.py
# (stub-take review ACCEPT; production module since glitch-06's 09:02 ruling), named here as DATA only: this module
# runs no process and imports nothing for it: box/rules_scanner.real_rules_scanner reads this record and checks its own
# pin and factory against it (moved there 14 Oct 2026: a lazy import here broke test_sidecar's default-deny audit). The pin is gitleaks 8.30.1, the official linux x64 release, at its athena path; the
# stub takes on athena measured the binary's sha256 and version line (lane-reports/stub-take-20261014,
# stub-take-run1..4.json; test_rules_scanner binds the pin to them, test_scan_record binds this record to the module).
RULES_SCANNER = {"adapter": "box.rules_scanner", "factory": "gitleaks_scanner", "version": "8.30.1",
                 "sha256": "88f91962aa2f93ac6ab281d553b9e125f5197bbbce38f9f2437f7299c32e5509",
                 "binary": "/home/javier/gap4-tools/gitleaks-8.30.1/gitleaks"}
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
    values = {"rules_scanner": RULES_SCANNER, "furniture": FURNITURE}
    return {f: why for f, why in _PENDING_WHY.items() if values[f] == PENDING}


def real_rules_scanner() -> dict:
    """The real rules scanner's RECORD (a copy): refused while it is PENDING or off its closed shape. This module runs no
    process and imports nothing to check it (test_sidecar's default-deny audit); the binding to the adapter, its pin and
    its factory is box/rules_scanner.real_rules_scanner(), which reads this record. Build the scan once per walk with
    `rules_scanner.real_rules_scanner().build(runtime, report_dir)`."""
    if RULES_SCANNER == PENDING:
        raise NotReady("the real rules scanner is PENDING (gitleaks on athena)")
    rec = RULES_SCANNER
    if not isinstance(rec, dict) or set(rec) != {"adapter", "factory", "version", "sha256", "binary"} \
            or rec["adapter"] != "box.rules_scanner" or rec["factory"] != "gitleaks_scanner":
        raise NotReady("the rules scanner record does not name the reviewed adapter, box/rules_scanner.py")
    return dict(rec)


def furniture_positions(harness: str):
    """Where `harness` writes its own account fields: refused while FURNITURE is PENDING."""
    if FURNITURE == PENDING:
        raise NotReady("the per-harness furniture positions are PENDING (measured on the stub take)")
    return FURNITURE[harness]


# ------------------------------------------------------------------------------------------------- login files
# Wave 4 merge, binding 5 review round 1 (glitch-f3's ruling under Javier's delegation; the merge-time exception to
# this lane, extended): the repository walk reads the real path (B5R1-1) and the owner is the real uid (B5R1-3), as
# run_take.read_login reads them.
def _real_path(path: str) -> str:
    return os.path.realpath(path)


def _in_git_repository(path: str) -> bool:
    d = os.path.dirname(_real_path(path))
    while True:
        if os.path.lexists(os.path.join(d, ".git")):
            return True
        up = os.path.dirname(d)
        if up == d:
            return False
        d = up


def _owned(st) -> bool:
    return st.st_uid == os.getuid()


def _name_allowed(name, allowed) -> bool:
    if not isinstance(allowed, (tuple, list, set)) or not allowed or not all(isinstance(a, str) for a in allowed):
        raise LoginError("the allowed login names are a non-empty tuple, list or set of names")
    return name in allowed


def _value_text(value: bytes) -> str:
    return value.decode("ascii")


def read_login(path: str, name: str, *, allowed) -> str:
    """The value of a login file `NAME=<value>`, read at run time and never written down. Refused (LoginError, whose
    message names the rule broken and never the content) unless the file keeps the rule. `allowed` is the caller's
    closed set of login names (binding 5: run_take.LOGIN_VARIABLE's values)."""
    if name == "-":            # run_take.NO_LOGIN (this module never imports run_take): glitch-06's ruling 1
        raise LoginError("a Codex row has no environment login: its login is the lease (read_lease_tokens)")
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise LoginError("the variable name is upper-case letters, digits and underscores")
    if not _name_allowed(name, allowed):
        raise LoginError("the variable name is not one of the allowed login names")
    if not isinstance(path, str) or not os.path.isabs(path):
        raise LoginError("the login file is named by an absolute path")
    try:
        st = os.lstat(path)
    except OSError:
        raise LoginError("the login file cannot be found") from None
    if not stat.S_ISREG(st.st_mode):
        raise LoginError("the login file is not a plain file (a link or a special file is refused)")
    if stat.S_IMODE(st.st_mode) != 0o600:
        raise LoginError("the login file's mode is not 600")
    if not _owned(st):
        raise LoginError("the login file is not owned by its reader")
    if _in_git_repository(path):
        raise LoginError("the login file sits inside a git repository")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise LoginError("the login file cannot be opened") from None
    try:
        data = os.read(fd, LOGIN_MAX_BYTES + 1)
    finally:
        os.close(fd)
    m = _LOGIN_LINE.fullmatch(data) if len(data) <= LOGIN_MAX_BYTES else None
    if not m or m.group(1).decode() != name:
        raise LoginError("the login file is not exactly one line NAME=<at least 20 ASCII characters, no whitespace, "
                         f"no double quote>, at most {LOGIN_MAX_BYTES} bytes")
    try:
        return _value_text(m.group(2))
    except UnicodeDecodeError:
        raise LoginError("the login file's value is not ASCII") from None


# The Codex lease's registered auth.json (glitch-06, 14 Oct 2026, ruling on the lease postflight review's MINOR 3):
# every login value is in the exact-value scan, so a Codex take's secrets carry the lease's access and refresh tokens.
# The two names are read under any JSON object of the file (their nesting is the CLI's, not ours); each must be found.
LEASE_TOKEN_KEYS = ("access_token", "refresh_token")
LEASE_MAX_BYTES = 1024 * 1024


def _lease_values(node, key, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                out.append(v)
            _lease_values(v, key, out)
    elif isinstance(node, list):
        for v in node:
            _lease_values(v, key, out)


def read_lease_tokens(path: str) -> list:
    """The access and refresh token values of a Codex lease's registered auth.json, read at run time and never written
    down. Refused (LoginError, naming the rule broken and never the content) unless the file is an absolute, plain
    (never a link or special) file, mode 600, owned by its reader, at most LEASE_MAX_BYTES of JSON, and each of
    LEASE_TOKEN_KEYS holds single-line strings of at least MIN_LENGTH["token"]. Opened as read_login opens a login
    file (no link followed, never blocking); like read_login, it does not bind the read to the check by inode
    (test_sidecar's closed vocabulary for this module holds no fstat)."""
    if not isinstance(path, str) or not os.path.isabs(path):
        raise LoginError("the lease file is named by an absolute path")
    try:
        st = os.lstat(path)
    except OSError:
        raise LoginError("the lease file cannot be found") from None
    if not stat.S_ISREG(st.st_mode):
        raise LoginError("the lease file is not a plain file (a link or a special file is refused)")
    if stat.S_IMODE(st.st_mode) != 0o600:
        raise LoginError("the lease file's mode is not 600")
    if not _owned(st):
        raise LoginError("the lease file is not owned by its reader")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise LoginError("the lease file cannot be opened") from None
    try:
        data = os.read(fd, LEASE_MAX_BYTES + 1)
    except OSError:
        raise LoginError("the lease file cannot be read") from None
    finally:
        os.close(fd)
    if len(data) > LEASE_MAX_BYTES:
        raise LoginError(f"the lease file is at most {LEASE_MAX_BYTES} bytes")
    # a nesting past the recursion limit refuses by rule (review of b9f876b5, MINOR 2): RecursionError is caught as
    # its base RuntimeError, already in test_sidecar's closed name set for this module (that set is not widened)
    try:
        doc = json.loads(data.decode("utf-8"))
        found_by_key = {}
        for key in LEASE_TOKEN_KEYS:
            found_by_key[key] = []
            _lease_values(doc, key, found_by_key[key])
    except (UnicodeDecodeError, ValueError, RuntimeError):
        raise LoginError("the lease file is not JSON within the nesting the reader walks") from None
    values = []
    for key in LEASE_TOKEN_KEYS:
        found = found_by_key[key]
        if not found:
            raise LoginError(f"the lease file holds no {key}")
        for v in found:
            if not isinstance(v, str) or len(v) < MIN_LENGTH["token"]:
                raise LoginError(f"a {key} is a string of at least {MIN_LENGTH['token']} characters")
            if "\n" in v or "\r" in v:
                raise LoginError(f"a {key} is a single-line string")
            if v not in values:
                values.append(v)
    return values

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


def _finding_ok(f) -> bool:
    return isinstance(f, dict) and set(f) == {"path", "line", "rule"}


def _survived(after: bytes, needles) -> bool:
    return any(n in after for n, _ in needles)


def _require_scanner(scanner):
    if scanner is None or not callable(scanner):
        raise NotReady("a real scan needs a callable rules scanner: build it per walk with "
                       "rules_scanner.real_rules_scanner().build(runtime, report_dir)")


def _require_files(files):
    if not files:
        raise ScanError("no file to scan: an empty commit list never passes (fold 2, W4C1-3)")


def _require_search(secrets):
    if not any(item[0] in ("token", "key") for item in secrets if isinstance(item, tuple) and item):
        raise ScanError("no token or key to search for: a scan that searches for none never passes (fold 2, W4C1-3)")


def _strings(node, out):
    """Every string in a decoded JSON value, keys included."""
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for k, v in node.items():
            out.append(k)
            _strings(v, out)
    elif isinstance(node, list):
        for v in node:
            _strings(v, out)
    return out


def _tool_uses(data: bytes) -> dict:
    """{tool_use id: [(tool name, its input)]} over every JSON record of a file (main thread or a sub-agent's)."""
    uses = {}

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "tool_use" and isinstance(node.get("id"), str):
                uses.setdefault(node["id"], []).append((node.get("name"), node.get("input")))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    for line in _lines(data):
        try:
            walk(json.loads(line))
        except ValueError:
            continue
    return uses


# The Bash shapes OD57 admits (glitch-b5's ruling of 16 Oct 2026, after walk w167): the command, split on &&, ||, ;
# and | and shell-tokenised, has a grep or cat segment, after any leading cd segments only, naming a path that ends in
# _references/environment.md. A parse failure, $(...), backticks, a process substitution, any other shell
# operator, or a segment opening with a wrapper (eval, sh -c, bash -c and kin) refuses. Admitting less is fine.
_RULED_SEPARATORS = ("&&", "||", ";", "|")
_RULED_REDIRECTS = (">", ">>", "<", ">&")
_RULED_WRAPPERS = ("eval", "sh", "bash", "zsh", "dash", "ksh", "exec", "source", ".", "xargs", "env", "command",
                   "builtin", "sudo", "nohup", "timeout")
_RULED_DOC = "_references/environment.md"


def _ruled_bash(cmd) -> bool:
    """A Bash command OD57 admits (the shapes above)."""
    if not isinstance(cmd, str) or any(x in cmd for x in ("$(", "`", "<(", ">(")):
        return False
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return False
    segments, cur = [], []
    for t in tokens:
        if t in _RULED_SEPARATORS:
            segments.append(cur)
            cur = []
        elif t and set(t) <= set("();<>|&") and t not in _RULED_REDIRECTS:
            return False
        else:
            cur.append(t)
    segments.append(cur)
    if "eval" in tokens or any(not seg or seg[0] in _RULED_WRAPPERS for seg in segments):
        return False
    i = 0
    while i < len(segments) and segments[i][0] == "cd" and len(segments[i]) == 2:
        i += 1
    if i == len(segments) or segments[i][0] not in ("grep", "cat"):
        return False
    return any(t == _RULED_DOC or t.endswith("/" + _RULED_DOC) for t in segments[i][1:])


def _ruled_tool(uses, tool_use_id) -> bool:
    """A Read, or a Bash command _ruled_bash admits: one tool_use with that id, no other."""
    got = uses.get(tool_use_id) if isinstance(tool_use_id, str) else None
    if not got or len(got) != 1:
        return False
    name, inp = got[0]
    if name == "Read":
        return True
    cmd = inp.get("command") if name == "Bash" and isinstance(inp, dict) else None
    return _ruled_bash(cmd)


def _blocks(node, out):
    """Every tool_result block in a record (outside its own tool-result keys)."""
    if isinstance(node, dict):
        if node.get("type") == "tool_result":
            out.append(node)
        for k, v in node.items():
            if k not in _TOOL_RESULT_KEYS:
                _blocks(v, out)
    elif isinstance(node, list):
        for v in node:
            _blocks(v, out)
    return out


def _tool_result_strings(node, uses, out):
    """The strings a ruled tool's result carries: a tool_result block's content (a string, or its text items), and
    every string under a record's own tool-result key (toolUseResult; tool_use_result in a stream) when every
    tool_result block of that record is a ruled tool's."""
    if isinstance(node, dict):
        if node.get("type") == "tool_result" and _ruled_tool(uses, node.get("tool_use_id")):
            c = node.get("content")
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, list):
                out += [i["text"] for i in c if isinstance(i, dict) and i.get("type") == "text"
                        and isinstance(i.get("text"), str)]
        for k, v in node.items():
            if k in _TOOL_RESULT_KEYS:
                blocks = _blocks(node, [])
                if blocks and all(_ruled_tool(uses, x.get("tool_use_id")) for x in blocks):
                    _strings(v, out)
            else:
                _tool_result_strings(v, uses, out)
    elif isinstance(node, list):
        for v in node:
            _tool_result_strings(v, uses, out)
    return out


def _ruled_text(body: bytes, ruling, uses) -> str | None:
    """The ruled line's text when this JSON record carries it only as whole lines of ruled tools' results, else
    None."""
    try:
        rec = json.loads(body)
    except ValueError:
        return None
    found, hits = None, 0
    for s in _tool_result_strings(rec, uses, []):
        for ln in s.split("\n"):
            for m in (0, _RULED_PREFIX.match(ln).end()):
                rest = ln[m:].encode("utf-8", "surrogateescape")
                if len(rest) == ruling["bytes"] and _sha(rest) == ruling["sha256"]:
                    found, hits = rest.decode(), hits + 1
                    break
    if found is None:
        return None
    # the text must sit in the record only where it was counted, and appear raw exactly as often (it needs no JSON
    # escape), so the probe below removes those occurrences and nothing else
    if json.dumps(found)[1:-1] != found or sum(x.count(found) for x in _strings(rec, [])) != hits \
            or body.count(found.encode()) != hits:
        return None
    return found


def _ruled_findings(scanner, files, findings) -> tuple:
    """(still refused, admitted) for the rule findings. A finding is admitted only when its rule has a ruling, its file
    is agent text, its line carries the ruled text as tool-result lines alone, and the rules scanner, run again over
    a probe copy of the file with exactly those occurrences removed, no longer reports that rule on that line."""
    kinds = dict(files)
    refused, admitted, candidates = [], [], {}
    for f in findings:
        rulings = [r for r in RULED_LINES if r["rule"] == f["rule"]]
        if rulings and kinds.get(f["path"]) in MASKABLE:
            with open(f["path"], "rb") as fh:
                data = fh.read()
            lines = _lines(data)
            if f["line"] <= len(lines):
                body = lines[f["line"] - 1].rstrip(b"\n")
                text = _ruled_text(body, rulings[0], _tool_uses(data))
                if text is not None:
                    candidates.setdefault(f["path"], []).append((f, rulings[0], text))
                    continue
        refused.append(f)
    for path, group in candidates.items():
        with open(path, "rb") as fh:
            lines = _lines(fh.read())
        for f, _, text in group:
            n = f["line"] - 1
            lines[n] = lines[n].replace(text.encode(), b"")
        work = tempfile.mkdtemp(prefix="ruled-probe-")
        probe = os.path.join(work, os.path.basename(path))
        try:
            with open(probe, "xb") as fh:
                fh.write(b"".join(lines))
            again = scanner([probe])
        finally:
            if os.path.lexists(probe):
                os.unlink(probe)
            os.rmdir(work)
        for g in again:
            if not _finding_ok(g):
                raise ScanError("a rules-scanner finding is {path, line, rule}")
        for f, ruling, _ in group:
            # a probe finding of the rule whose line is not a number fails closed (aegis review of 4043a29, finding 2)
            if any(g["rule"] == f["rule"] and (type(g["line"]) is not int or g["line"] == f["line"]) for g in again):
                refused.append(f)
            else:
                admitted.append({"path": f["path"], "line": f["line"], "rule": f["rule"], "ruling": ruling["ruling"]})
    return refused, admitted


def _rules(scanner, files) -> tuple:
    """(every rules-scanner finding no exact ruling admits, refused; the admitted ones, each naming its ruling)."""
    found = []
    for f in scanner([p for p, _ in files]):
        if not _finding_ok(f):
            raise ScanError("a rules-scanner finding is {path, line, rule}")
        found.append(f)
    still, admitted = _ruled_findings(scanner, files, found)
    return [{"path": f["path"], "line": f["line"], "kind": RULE_KIND,
             "why": f"the rules scanner's rule {f['rule']!r}"} for f in still], admitted


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


def replacement_marker(replacement_id: str) -> bytes:
    """The fixed marker bytes a witness replacement id stands for (the pinned MARKERS map); an unknown id refuses."""
    for kind, rid in REPLACEMENT_IDS.items():
        if rid == replacement_id:
            return MARKERS[kind].encode("utf-8")
    raise ScanError("an unknown replacement id (the witness names only the pinned markers)")


def _line_offsets(data: bytes) -> list:
    """The absolute byte offset where each of _lines(data) starts."""
    out, at = [], 0
    for line in _lines(data):
        out.append(at)
        at += len(line)
    return out


def _replacements(before: bytes, masked, needles) -> list:
    """The witness spans of one file, derived only from its masked entries (the successful masking branch): each
    entry's line and in-line start, its end from the same longest-first selection, as absolute original offsets."""
    if not masked:
        return []
    offsets, lines = _line_offsets(before), _lines(before)
    out = []
    for m in masked:
        line = lines[m["line"] - 1]
        body = line[:-1] if line.endswith(b"\n") else line
        ends = [e for s, e, k in _spans(body, needles) if s == m["offset"] and k == m["kind"]]
        if len(ends) != 1:
            raise ScanError(f"{m['path']}: a masked entry has no single span; nothing written")
        base = offsets[m["line"] - 1]
        out.append({"start": base + m["offset"], "end": base + ends[0], "kind": m["kind"],
                    "replacement_id": REPLACEMENT_IDS[m["kind"]]})
    return sorted(out, key=lambda r: r["start"])


def _rebuild(before: bytes, replacements) -> bytes:
    out, at = [], 0
    for r in replacements:
        if not (at <= r["start"] < r["end"] <= len(before)):
            raise ScanError("witness spans are nonempty, disjoint, increasing and inside the original")
        out += [before[at:r["start"]], replacement_marker(r["replacement_id"])]
        at = r["end"]
    out.append(before[at:])
    return b"".join(out)


def _witness(path: str, before: bytes, after: bytes, replacements) -> dict:
    """One file's witness; fails closed (ScanError, before anything is written) unless the spans rebuild `after`."""
    if _rebuild(before, replacements) != after:
        raise ScanError(f"{path}: the witness spans do not rebuild the masked bytes; nothing written")
    return {"schema": WITNESS_SCHEMA, "original_sha256": _sha(before), "published_sha256": _sha(after),
            "original_bytes": len(before), "published_bytes": len(after), "replacements": replacements}


def _scan_core(files, secrets, scanner, holdout_matcher):
    """The shared scan: (the scan result, {path: witness}). Each file's witness is built and checked before that
    file is written, so a refused witness never writes its file."""
    _require_scanner(scanner)   # the injected callable (interface 14); never RULES_SCANNER
    files, secrets = list(files), list(secrets)
    _require_files(files)
    _require_search(secrets)
    _check_inputs(files, secrets)
    needles = _needles(secrets)
    masked, refused, records, witnesses = [], [], [], {}
    for path, kind in files:
        with open(path, "rb") as fh:
            before = fh.read()
        new, m, r = _scan_file(path, kind, before, needles)
        after = before if new is None else new
        if new is not None:
            if _survived(after, needles):
                raise ScanError(f"{path}: a value survived its masking; nothing written")
            if [ln for ln in _lines(before) if not _spans(ln, needles)] != \
                    [ln for ln, old in zip(_lines(after), _lines(before)) if not _spans(old, needles)]:
                raise ScanError(f"{path}: masking changed a line it should not touch; nothing written")
        witnesses[path] = _witness(path, before, after, _replacements(before, m if new is not None else [],
                                                                      needles))
        if new is not None:
            _write(path, after)
        masked += m
        refused += r
        if holdout_matcher is not None:
            refused += _holdout(holdout_matcher, path, after)
        records.append({"path": path, "sha256_before": _sha(before), "sha256_after": _sha(after)})
    rule_refused, ruled = _rules(scanner, files)
    refused += rule_refused
    result = {"masked": masked, "events": len(masked), "refused": refused, "files": records,
              "holdout": NOT_CHECKED if holdout_matcher is None else CHECKED, "ruled": ruled}
    return result, witnesses


def scan(files, secrets, *, rules_scanner, holdout_matcher=None) -> dict:
    """Scan every file of a take's commit (see the module docstring)."""
    return _scan_core(files, secrets, rules_scanner, holdout_matcher)[0]


def scan_with_witness(files, secrets, *, rules_scanner, holdout_matcher=None) -> tuple:
    """scan's result unchanged, plus {path: witness} for every scanned file (unchanged files carry an empty
    replacement list). A witness carries offsets, lengths, kinds, fixed marker ids and whole-file sha256s only: never
    a secret's value, nor a digest of a value alone."""
    return _scan_core(files, secrets, rules_scanner, holdout_matcher)


def passed(result: dict) -> bool:
    """May the caller commit? Only with nothing refused. A "not-checked" holdout record does not refuse here; it
    is cleared by the later gate inside aegis, before any push."""
    return not result["refused"]
