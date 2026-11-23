#!/usr/bin/env python3
"""Lane vendor-admission T4 (plan v4 section 9, NIT 7): a piece's edited files are disjoint from the native readers'
source lists. Usage: check_vendor_sources.py <piece> <file> ...; each file is a path under evals/gap-study-4/. Exit 1
when a file is in native_reader_registration.READER_SOURCES or CODEX_SOURCES, except drive.py for piece P0, whose
edit A is the drive.py edit the plan rules (section 6), and for piece EB, edits B and C (glitch-b5 rounds 14 and 15,
review e-71a2b94 findings 1 and 2: the vendor turn envelopes, and their and the snapshots' sha256 rebound to the
scan's masked bytes). Piece EB naming drive.py also checks both edits' whole diff: each edit must be present, and
drive.py with edit B's lines (TakeDriver._take_records' first `if vendor:` branch after its first statement) and edit
C's lines (the one statement of TakeDriver.drive right after the drive scan's `if not _scan_record.passed(scan):`, an
`if` whose test requires the row's harness in VENDOR_HARNESSES, round 16) taken out must be, byte for byte, drive.py
before edit B (PRE_EDIT_B_DRIVE_SHA256, its text at f628e9d8), so no other drive.py line moves. Edit D (lane vendor-b11
round 4, glitch-26's ruling R4-1: EDIT_D_RULING) is recorded the same way: its hunks (EDIT_D) are taken out by their
text before edits C and B, and drive.py after it is pinned whole (POST_EDIT_D_DRIVE_SHA256). Edit E (lane vendor-b25,
glitch-26's ruling 2: EDIT_E_RULING) is recorded as edit D is and taken out first (POST_EDIT_E_DRIVE_SHA256). Edit F (lane
vendor-b26, glitch-26's ruling 6: EDIT_F_RULING) is recorded the same way and taken out before E (POST_EDIT_F_DRIVE_SHA256).
Any such edit after
Javier's acceptance commit makes production_readers refuse, so a piece naming one is a red check, never a note.

Piece B17 (glitch-26's ruling B17-5, lane vendor-b17 round 2, Mon 19 Oct 2026: OD57's read shapes reach the drive
scan) admits drive.py only with its exact edit: the module function scan_read_shapes (B17_HELPER_SHA256 pins its text
from its `def` line to its last line) after two blank lines, and in each of the drive's three `_scan_record.scan(...)`
calls one line holding only `read_shapes=scan_read_shapes(row),` in TakeRepo._commit_step and TakeDriver.drive, and
`read_shapes=scan_read_shapes(entry),` in WalkRepo._commit_walk (B17_SITES, round 3). Every other drive.py line is then
bound by piece EB's check as before: edit_b_problems, edit_d_problems and without_edits read drive.py with B17's
lines taken out (so edit D's whole-file pin, POST_EDIT_D_DRIVE_SHA256, holds drive.py outside B17's exact lines), and
report any trace of B17 that is off its exact form."""

from __future__ import annotations

import ast
import hashlib
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import native_reader_registration as nrr  # noqa: E402

PIECES = ("PF", "P0", "P0b", "P1", "P2", "P3", "P4", "P5", "EB", "B17")
ALLOWED = {"P0": {"drive.py"}, "EB": {"drive.py"}, "B17": {"drive.py"}}
PRE_EDIT_B_DRIVE_SHA256 = "ea3917d4e4c1acc2078b1779bab0c6c47304aee920c8d2f2dc3423ec33934906"
B17_HELPER = "scan_read_shapes"
B17_HELPER_SHA256 = "f2ad5a5fae8467f8545fd55bb7295a1647d3af7568e8ec1c4a32ec9f992bd713"
B17_CALLS = 3
# Round 3 (glitch-26's B17-14, review a051f6e3 NIT 4): each call site's argument name, by its enclosing function:
# TakeRepo._commit_step and TakeDriver.drive pass the row, WalkRepo._commit_walk its register entry.
B17_SITES = {"_commit_step": "row", "drive": "row", "_commit_walk": "entry"}


def _scan_calls(tree) -> list:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr in ("scan", "scan_with_witness") and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "_scan_record"]


def _call_sites(tree) -> dict:
    """{id(scan call): the name of the innermost function holding it}."""
    out = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for c in _scan_calls(fn):
                out[id(c)] = fn.name                # ast.walk visits outer functions first, so the inner one wins
    return out


def b17_spans(src: str) -> tuple:
    """(spans, problems): the 1-based (first, last) line spans of piece B17's drive.py edit, and what is off its exact
    form. No helper and no read_shapes keyword: no spans and no problems (drive.py before B17)."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [], [f"piece B17: drive.py does not parse: {e}"]
    lines = src.splitlines(keepends=True)
    calls = _scan_calls(tree)
    helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == B17_HELPER]
    keywords = [(c, k) for c in calls for k in c.keywords if k.arg == "read_shapes"]
    if not helpers and not keywords:
        return [], []
    spans, out = [], []
    if len(helpers) != 1:
        out.append(f"piece B17: drive.py defines {B17_HELPER} {len(helpers)} times, not once")
    else:
        h = helpers[0]
        text = "".join(lines[h.lineno - 1:h.end_lineno])
        if h.decorator_list or hashlib.sha256(text.encode("utf-8")).hexdigest() != B17_HELPER_SHA256:
            out.append(f"piece B17: {B17_HELPER}'s text is not the pinned one (B17_HELPER_SHA256)")
        if h.lineno < 3 or lines[h.lineno - 3] != "\n" or lines[h.lineno - 2] != "\n":
            out.append(f"piece B17: {B17_HELPER} is not preceded by two blank lines")
        spans.append((h.lineno - 2, h.end_lineno))
    if len(calls) != B17_CALLS or len(keywords) != B17_CALLS or {id(c) for c, _ in keywords} != {id(c) for c in calls}:
        out.append(f"piece B17: drive.py's {len(calls)} scan calls carry {len(keywords)} read_shapes keywords, not one "
                   f"in each of {B17_CALLS}")
    sites = _call_sites(tree)
    if sorted(sites.get(id(c)) or "" for c in calls) != sorted(B17_SITES):
        out.append(f"piece B17: drive.py's scan calls sit in {sorted(sites.get(id(c)) or '?' for c in calls)}, not "
                   f"{sorted(B17_SITES)}")
    for c, k in keywords:
        name = B17_SITES.get(sites.get(id(c)), "?")
        line = lines[k.value.lineno - 1]
        if k.value.lineno != k.value.end_lineno or not re.fullmatch(
                r" +read_shapes=scan_read_shapes\(" + re.escape(name) + r"\),\n", line):
            out.append(f"piece B17: drive.py line {k.value.lineno} is not one line holding only "
                       f"read_shapes=scan_read_shapes({name}),")
        spans.append((k.value.lineno, k.value.lineno))
    return sorted(spans), out


def b17_problems(src: str) -> list:
    """What is off piece B17's exact drive.py edit (nothing when drive.py holds no trace of it)."""
    return b17_spans(src)[1]


def without_b17(src: str) -> str:
    """drive.py's text with piece B17's lines taken out (before B17, the text itself)."""
    spans = b17_spans(src)[0]
    drop = {n for first, last in spans for n in range(first, last + 1)}
    return "".join(line for n, line in enumerate(src.splitlines(keepends=True), 1) if n not in drop)

# Edit D (lane vendor-b11 round 4, glitch-26's ruling R4-1, Mon 19 Oct 2026): the drive-side wiring of B11's per-turn
# config folder check, the round-3 proposed patch applied as it stood. Each hunk is (before, after): `after` occurs in
# drive.py exactly once, and replacing it with `before` takes the hunk out.
EDIT_D_RULING = ("R4-1 (glitch-26, lane vendor-b11 round 4): TakeDriver.config_folder builds the take's config folder "
                 "record (ownership.config_folder) and harness_adapter_for hands it to the arm O and G adapters "
                 "(walk_driver binds the driver's); run_take.ConfigFolderRefused is routed as the settings guard's "
                 "problems are: before turn 1 a rehearsal, after it a stop for a ruling. A named exception on a native "
                 "reader source (as B12's edit of transcript_gemini.py was): no reader acceptance exists yet, so no "
                 "accepted bytes move.")
POST_EDIT_D_DRIVE_SHA256 = "b93bf6c5f40fa53257bffb7b147720886a252ab3051a64532eb04a9896d4eabd"
EDIT_D = (
    ("",
     "        self.config_stop = None        # B11: the config folder's problems that stopped an O or G take before turn k > 1\n"),
    ("",
     '    def config_folder(self, take, lease=None):\n'
     '        """B11 (lane vendor-b11 round 3): the take\'s run_take.ConfigFolder for its O or G turns, through the box\'s\n'
     '        census and reads of the config folder (ownership.config_folder): the take image, run tree, config folder and\n'
     "        model, the codex lease's placement record (`lease`, the adapter's login: bound to the take's uid map; None\n"
     '        for gemini), and the take\'s uid map."""\n'
     '        harness = (take.row.get("agent") or {}).get("harness")\n'
     '        uid_map = self.uid_map\n'
     "        if callable(uid_map):                       # read at run time (the take container's own map), or given\n"
     '            uid_map = uid_map(take)\n'
     '        return self.ownership.config_folder(self.runtime, image=take.spec.image, harness=harness,\n'
     '                                            run_tree=take.spec.run_tree, config_dir=take.config_dir,\n'
     '                                            model=take.row["model"], lease=lease, uid_map=uid_map,\n'
     '                                            caller_env=self.caller_env)\n'
     '\n'),
    ("",
     '                    except _run_take.ConfigFolderRefused as e:    # B11 (vendor-b11 R-CF): refused before its exec,\n'
     '                        if n == 1:                                # routed as the settings guard is: a rehearsal\n'
     '                            self._refused(take, e)\n'
     '                            ok = False\n'
     '                        else:                                     # after turn 1, a stop for a ruling\n'
     '                            take.config_stop = f"pre-{n}: the config folder: {\'; \'.join(e.problems)}"\n'
     '                        break\n'),
    ("",
     '        if take.config_stop is not None:          # B11 after turn 1, as the settings guard: cleaned and scanned\n'
     '            raise DriveRefused(f"{take.config_stop}: no further turn is sent; the take is kept for a human ruling "\n'
     '                               f"(no registered harness-error row reads it), never a re-run")\n'),
    ('                        rollout_for=None, caller_env=None, config_view=None):\n',
     '                        rollout_for=None, caller_env=None, config_view=None, config_folder=None):\n'),
    ('                      counters_for=lambda: counters_for(take), clock=clock, caller_env=caller_env)\n',
     '                      counters_for=lambda: counters_for(take), clock=clock, caller_env=caller_env,\n'
     "                      # B11 (vendor-b11 R-CF): the take's config folder record (walk_driver binds the driver's)\n"
     '                      config_folder=None)\n'
     '        if callable(config_folder):\n'
     '            common["config_folder"] = config_folder(take, common["login_file"] if harness == "codex" else None)\n'),
    ('                                        config_view=lambda take: bound["driver"].config_view(take)),\n',
     '                                        config_view=lambda take: bound["driver"].config_view(take),\n'
     '                                        config_folder=lambda take, lease: bound["driver"].config_folder(take, lease)),\n'),
)


# Edit E (lane vendor-b25, glitch-26's ruling 2, Wed 21 Oct 2026; the Codex reader review's M1): the production
# Codex cross-check binds each rollout turn's recorded prompt and requested model to the launch side. Recorded as edit
# D is: each hunk (before, after), `after` in drive.py exactly once; taken out first (it was made last), and drive.py
# after it pinned whole (POST_EDIT_E_DRIVE_SHA256), so edit D's pin still holds drive.py with E taken out.
EDIT_E_RULING = ("B25-2 (glitch-26, lane vendor-b25, ruling 2): drive.codex_cross_check takes `sent` (the ledger rows' "
                 "sent lines) and `model` (the row's requested model) and hands them to "
                 "native_reader_registration.codex_join_session, the one join acceptance also runs, so a rollout whose "
                 "UserMessage or turn_context model is not the launched one is DISAGREE. A named exception on a native "
                 "reader source, as edit D was: no reader acceptance exists yet, so no accepted bytes move.")
POST_EDIT_E_DRIVE_SHA256 = "4a1835d7c1622ce79b80ee6df08450b8c1564e3fe9a6f7a57011e1bd44f25120"
EDIT_E = (
    ('                 else codex_cross_check(take.folder, take.native_snapshots, [t.exit_code for t in turns])\n',
     '                 else codex_cross_check(take.folder, take.native_snapshots, [t.exit_code for t in turns],\n'
     '                                        sent=[r.get("sent") for r in rows], model=row.get("model"))\n'),
    ('def codex_cross_check(take_folder, refs, exit_codes, *, readers=None) -> dict:\n'
     '    """Codex slice 3: D8\'s cross-check for a Codex take, through the ONE join the acceptance check also runs\n'
     '    (native_reader_registration.codex_join_session): each turn\'s exec stream joined to that turn of the take\'s last\n'
     '    retained rollout. `pending` without a registered Codex reader; `refused` on any disagreement, an extra or missing\n'
     '    turn, or an incomplete turn; `agreed` only when every turn joins complete."""\n',
     'def codex_cross_check(take_folder, refs, exit_codes, *, sent, model, readers=None) -> dict:\n'
     '    """Codex slice 3: D8\'s cross-check for a Codex take, through the ONE join the acceptance check also runs\n'
     '    (native_reader_registration.codex_join_session): each turn\'s exec stream joined to that turn of the take\'s last\n'
     '    retained rollout, its recorded prompt to the line sent (`sent`, the ledger rows\') and its requested model to the\n'
     '    take\'s (`model`; lane vendor-b25, Codex review M1). `pending` without a registered Codex reader; `refused` on any\n'
     '    disagreement, an extra or missing turn, or an incomplete turn; `agreed` only when every turn joins complete."""\n'),
    ('    got = _registration.codex_join_session(raw, streams, list(exit_codes))\n',
     '    got = _registration.codex_join_session(raw, streams, list(exit_codes), sent=list(sent), model=model)\n'),
)


# Edit F (lane vendor-b26, glitch-26's ruling 6 on the B26 design, Wed 21 Oct 2026): the production Gemini history
# join (native_history_record) also requires each retained snapshot to be a byte prefix of the next one. Recorded as
# edit E is; taken out first (it was made last), and drive.py after it pinned whole (POST_EDIT_F_DRIVE_SHA256), so
# edit E's pin still holds drive.py with F taken out.
EDIT_F_RULING = ("B26-6 (glitch-26, lane vendor-b26, ruling 6): drive.native_history_record runs "
                 "native_reader_registration.gemini_snapshot_prefixes after the history join for a Gemini take, so a "
                 "later native snapshot that is not a byte extension of the one before it is refused; the recorder only "
                 "appends, which is what lets the reader read a re-record's retired originals. vendor_provenance's "
                 "contract is unchanged. A named exception on a native reader source, as edits D and E were: no reader "
                 "acceptance exists yet, so no accepted bytes move.")
POST_EDIT_F_DRIVE_SHA256 = "4f86970184f246f35dd688a9c30a38473725a6100dc97d856c4006b95145777f"
EDIT_F = (
    ('        facts = _vendor_provenance.session_history_facts(harness, Path(session_dir), list(refs), readers=readers)\n',
     '        facts = _vendor_provenance.session_history_facts(harness, Path(session_dir), list(refs), readers=readers)\n'
     '        if harness == "gemini":\n'
     '            _registration.gemini_snapshot_prefixes(Path(session_dir), list(refs))\n'),
)


# Edit G (lane fold6/kill-leftovers, glitch-45's ruling (a), Sun 1 Nov 2026, under Javier's standing delegation):
# TakeDriver._postflight passes the take's own session id and run tree to preflight.postflight, which then admits a
# killed claude-code take's producer-bound sessions/ pair. One line, edited in place; taken out first (it was made
# last) by without_edit_f, and drive.py after it pinned whole (POST_EDIT_G_DRIVE_SHA256), so edit F's pin still holds
# drive.py with G taken out. A checker-code change: the checker digests move and a recheck wave follows.
EDIT_G_RULING = ("fold6 (a) (glitch-45, lane fold6/kill-leftovers): drive.TakeDriver._postflight passes "
                 "session_id=take.identity's session id and run_tree=take.spec.run_tree to preflight.postflight")
POST_EDIT_G_DRIVE_SHA256 = "59f8a9c17dc3d372c391f3d65382fb780507452d63dcf339176c80ae5d998190"
EDIT_G = (
    ('            post = _preflight.postflight(take.config_dir, row["agent"]["harness"])\n',
     '            post = _preflight.postflight(take.config_dir, row["agent"]["harness"], session_id=(take.identity or {}).get("session_id"), run_tree=take.spec.run_tree if take.spec else None)  # noqa: E501  lane fold6/kill-leftovers\n'),
)


def without_edit_g(src: str) -> str:
    """drive.py's text with edit G taken out; ValueError when its hunk is not there once."""
    for k, (before, after) in enumerate(EDIT_G):
        if src.count(after) != 1:
            raise ValueError(f"edit G's hunk {k} is in drive.py {src.count(after)} times, not once")
        src = src.replace(after, before)
    return src


def edit_g_problems(src: str) -> list:
    """Edit G's pin: drive.py with piece B17's exact lines taken out has the sha256 recorded after edit G."""
    got = hashlib.sha256(without_b17(src).encode("utf-8")).hexdigest()
    return [] if got == POST_EDIT_G_DRIVE_SHA256 else [
        f"edit G: drive.py's sha256 {got[:12]}... is not the one pinned after edit G ({POST_EDIT_G_DRIVE_SHA256[:12]}...)"]


def without_edit_f(src: str) -> str:
    """drive.py's text with edits G (lane fold6) and F taken out, as without_edit_e does it; ValueError when a hunk is
    not there once."""
    src = without_edit_g(src)
    for k, (before, after) in enumerate(EDIT_F):
        if src.count(after) != 1:
            raise ValueError(f"edit F's hunk {k} is in drive.py {src.count(after)} times, not once")
        src = src.replace(after, before)
    return src


def edit_f_problems(src: str) -> list:
    """Edit F's pin: drive.py with piece B17's exact lines taken out has the sha256 recorded after edit F."""
    try:
        got = hashlib.sha256(without_edit_g(without_b17(src)).encode("utf-8")).hexdigest()
    except ValueError as e:
        return [f"edit G: {e}"]
    return [] if got == POST_EDIT_F_DRIVE_SHA256 else [
        f"edit F: drive.py's sha256 {got[:12]}... is not the one pinned after edit F ({POST_EDIT_F_DRIVE_SHA256[:12]}...)"]


def without_edit_e(src: str) -> str:
    """drive.py's text with edit E taken out, as without_edit_d does it; ValueError when a hunk is not there once."""
    for k, (before, after) in enumerate(EDIT_E):
        if src.count(after) != 1:
            raise ValueError(f"edit E's hunk {k} is in drive.py {src.count(after)} times, not once")
        src = src.replace(after, before)
    return src


def edit_e_problems(src: str) -> list:
    """Edit E's pin: drive.py with piece B17's exact lines and edit F taken out has the sha256 recorded after edit E."""
    try:
        got = hashlib.sha256(without_edit_f(without_b17(src)).encode("utf-8")).hexdigest()
    except ValueError as e:
        return [f"edit F: {e}"]
    return [] if got == POST_EDIT_E_DRIVE_SHA256 else [
        f"edit E: drive.py's sha256 {got[:12]}... is not the one pinned after edit E ({POST_EDIT_E_DRIVE_SHA256[:12]}...)"]


def edit_b_span(src: str):
    """(first, last), the 1-based lines of edit B in drive.py's text: every line of TakeDriver._take_records' first
    `if vendor:` branch after the branch's first statement (its cross_check), or None when the branch holds that
    statement alone; raises ValueError when there is no such branch."""
    for cls in ast.parse(src).body:
        if isinstance(cls, ast.ClassDef) and cls.name == "TakeDriver":
            for fn in cls.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == "_take_records":
                    for node in fn.body:
                        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "vendor":
                            body = node.body
                            return (body[0].end_lineno + 1, body[-1].end_lineno) if len(body) > 1 else None
    raise ValueError("drive.py has no TakeDriver._take_records `if vendor:` branch")


def without_edit_b(src: str) -> str:
    """drive.py's text with edit B's lines taken out (before edit B, the text itself)."""
    return _cut(src, edit_b_span(src))


def _scan_check(node) -> bool:
    """Whether `node` is the drive scan's `if not _scan_record.passed(scan):`."""
    t = node.test if isinstance(node, ast.If) else None
    return (isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not) and isinstance(t.operand, ast.Call)
            and isinstance(t.operand.func, ast.Attribute) and t.operand.func.attr == "passed"
            and isinstance(t.operand.func.value, ast.Name) and t.operand.func.value.id == "_scan_record")


ROW_HARNESS = ast.dump(ast.parse('row["agent"]["harness"]', mode="eval").body)


def _requires_vendor(test) -> bool:
    """Whether an `if` test requires the row's harness to be in VENDOR_HARNESSES (glitch-b5 round 16, review f-981e871
    NIT 4): the test is `row["agent"]["harness"] in VENDOR_HARNESSES` itself or an `and` holding it as one operand, so
    every other operand only narrows it; a `not in`, a negation, an `or`, a widened set or another left side is not."""
    def member(t) -> bool:
        return (isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.In)
                and ast.dump(t.left) == ROW_HARNESS
                and isinstance(t.comparators[0], ast.Name) and t.comparators[0].id == "VENDOR_HARNESSES")
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        return any(member(v) for v in test.values)
    return member(test)


def edit_c_span(src: str):
    """(first, last), the 1-based lines of edit C in drive.py's text: the one statement of TakeDriver.drive right after
    the drive scan's `if not _scan_record.passed(scan):`, when it is an `if` whose test requires the row's harness to be
    in VENDOR_HARNESSES (_requires_vendor), or None when it is not; raises ValueError when TakeDriver.drive holds no
    such scan check."""
    for cls in ast.parse(src).body:
        if isinstance(cls, ast.ClassDef) and cls.name == "TakeDriver":
            for fn in cls.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == "drive":
                    for k, node in enumerate(fn.body):
                        if _scan_check(node):
                            nxt = fn.body[k + 1] if k + 1 < len(fn.body) else None
                            if isinstance(nxt, ast.If) and _requires_vendor(nxt.test):
                                return (nxt.lineno, nxt.end_lineno)
                            return None
    raise ValueError("drive.py has no TakeDriver.drive `if not _scan_record.passed(scan):`")


def _cut(src: str, span) -> str:
    if span is None:
        return src
    lines = src.splitlines(keepends=True)
    return "".join(lines[:span[0] - 1] + lines[span[1]:])


def without_edit_c(src: str) -> str:
    """drive.py's text with edit C's lines taken out (before edit C, the text itself)."""
    return _cut(src, edit_c_span(src))


def without_edit_d(src: str) -> str:
    """drive.py's text with edit D taken out: each hunk's `after` replaced by its `before`; raises ValueError when a
    hunk's `after` is not in the text exactly once (edit D absent, partial or moved)."""
    for k, (before, after) in enumerate(EDIT_D):
        if src.count(after) != 1:
            raise ValueError(f"edit D's hunk {k} is in drive.py {src.count(after)} times, not once")
        src = src.replace(after, before)
    return src


def without_edits(src: str) -> str:
    """drive.py's text with piece B17's lines (by their spans), then edits E and D (by their text), C and B taken out:
    C before B, as it lies below B, so B's lines do not move."""
    return without_edit_b(without_edit_c(without_edit_d(without_edit_e(without_edit_f(without_b17(src))))))


def edit_d_problems(src: str) -> list:
    """Edit D's pin: drive.py with piece B17's exact lines taken out has the sha256 recorded after edit D
    (POST_EDIT_D_DRIVE_SHA256); B17's lines are bound by b17_problems."""
    try:
        got = hashlib.sha256(without_edit_e(without_edit_f(without_b17(src))).encode("utf-8")).hexdigest()
    except ValueError as e:
        return [f"edit E or F: {e}"]
    return [] if got == POST_EDIT_D_DRIVE_SHA256 else [
        f"edit D: drive.py's sha256 {got[:12]}... is not the one pinned after edit D ({POST_EDIT_D_DRIVE_SHA256[:12]}...)"]


def edit_b_problems(src: str) -> list:
    """Piece B17's lines, when drive.py holds any, exactly its edit; then, with them taken out, edits B, C and D, each
    present, and drive.py outside them drive.py before edit B."""
    b17 = b17_problems(src)
    if b17:
        return b17
    src = without_b17(src)
    try:
        src = without_edit_e(without_edit_f(src))
    except ValueError as e:
        return [f"edit E: {e}"]
    try:
        without_edit_d(src)
    except ValueError as e:
        return [f"edit D: {e}"]
    try:
        span, span_c = edit_b_span(src), edit_c_span(src)
    except (SyntaxError, ValueError) as e:
        return [f"edit B or C: {e}"]
    out = []
    if span is None:
        out.append("edit B: TakeDriver._take_records' vendor branch writes no turn envelopes (its one statement only)")
    if span_c is None:
        out.append("edit C: TakeDriver.drive rebinds nothing to the masked bytes right after the drive scan (no `if` "
                   "there whose test requires the row's harness in VENDOR_HARNESSES)")
    if out:
        return out
    if hashlib.sha256(without_edit_b(without_edit_c(without_edit_d(src))).encode("utf-8")).hexdigest() \
            != PRE_EDIT_B_DRIVE_SHA256:
        return [f"edits B, C and D: drive.py outside lines {span[0]}-{span[1]} (the vendor branch), "
                f"{span_c[0]}-{span_c[1]} (after the drive scan) and edit D's hunks is not drive.py before edit B"]
    return []


def problems(piece: str, files: list) -> list:
    if piece not in PIECES:
        return [f"{piece!r} is not a piece of the plan ({', '.join(PIECES)})"]
    if not files:
        return [f"piece {piece} names no file"]
    listed = set(nrr.READER_SOURCES) | set(nrr.CODEX_SOURCES)
    out = [f"piece {piece} edits {f}, which is in READER_SOURCES or CODEX_SOURCES" for f in files
           if f in listed and f not in ALLOWED.get(piece, set())]
    out += [f"piece {piece} names {f}, which is not a file under evals/gap-study-4/" for f in files
            if not (HERE / f).is_file()]
    if piece in ("EB", "B17") and "drive.py" in files and (HERE / "drive.py").is_file():
        text = (HERE / "drive.py").read_text(encoding="utf-8")
        if piece == "B17" and not b17_spans(text)[0]:
            out.append("piece B17: drive.py holds no B17 edit (scan_read_shapes and its three read_shapes lines)")
        out += (edit_b_problems(text) + edit_d_problems(text) + edit_e_problems(text) + edit_f_problems(text)
                + edit_g_problems(text))
    return out


def main(argv) -> int:
    if not argv:
        print("usage: check_vendor_sources.py <piece> <file> ...")
        return 2
    bad = problems(argv[0], argv[1:])
    for b in bad:
        print(f"check_vendor_sources: REFUSE: {b}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
