#!/usr/bin/env python3
"""CP5's coverage table: every row of coverage_today.md is bound to the bytes of GARS at the 6 Oct commit.

    python3 -B -W ignore evals/gap-study-4/tests/test_coverage.py

WHAT THE TABLE IS. `coverage_today.md` answers, one row per task pair, "would today's GARS (the 6 Oct tree:
hooks, deny rules, helpers) catch the trap's wrong move?", by a reader reading code at COMMIT, never by
running a model or GARS's own guard. This file parses that table and binds every answer to the commit.

THE COMMIT (glitch-f3's ruling 1, Thu 8 Oct 2026, under Javier's delegation). COMMIT is the last GARS main
commit of 6 Oct, pinned as a full sha. Its `gars/` tree equals SAME_GARS_AS's (main at 15:00 EDT that day):
`git diff --name-only SAME_GARS_AS COMMIT -- gars` prints nothing, and a test pins that. Only `gars/` paths
are ever cited (CITED_ROOT): the commit's tree also holds sealed records, which this lane never reads.

THE TABLE'S SHAPE (closed; parse() reads it). One markdown table, its header exactly COLUMNS, then one row
per pair:

  pair            a name in PAIRS, each exactly once; a name in DROPPED_ROWS carries DROPPED_MARK after it (W4F1-4),
                  and no other name does.
  trap's wrong move   in words, non-empty.
  caught          one of CAUGHT_VALUES.
  where           a cite: `<path>:<line>`, `<path>:<lo>-<hi>`, or `<path>@<mode>` (a file-permission answer,
                  the mode as `git ls-tree` prints it at COMMIT).
  excerpt         for a line cite, the cited code, verbatim and short; for a mode cite, the mode itself.
  reach           one of REACH_VALUES, or REACH_NONE (glitch-f3's ruling 2).
  reach where     a cite, as `where`.
  reach excerpt   as `excerpt`.

  Each reach value is bound to where its cites live (home_problems): `claude-only`, both under CLAUDE_HOMES;
  `claude-and-codex`, `where` in DECIDE_FILES (the files `guard_hook.decide` reads) and `reach where` in
  CODEX_HOMES; `every-agent`, neither cite in any of those (review round 1 of this lane, M4: a reach swapped
  inside the vocabulary stayed green before).
  `reach` is REACH_NONE exactly when `caught` is CAUGHT_NO, and then `reach where` and `reach excerpt` hold
  exactly DASH. A cell may be wrapped in one pair of backticks; a `|` inside a cell is written `\\|`.

WHAT A CITE MUST HOLD (cite_problems):
  - the path starts with CITED_ROOT, has no `..` segment, and is a file (a blob) at the commit;
  - a line range lies inside the file (lines counted at each "\\n", as git numbers them), with lo <= hi;
  - the excerpt, WHITESPACE-NORMALISED (every run of whitespace, line breaks included, read as one space,
    and the ends stripped; the cited lines are joined by one space before the same normalisation), is a
    substring of the cited lines;
  - the cite is TIGHT (this lane's decision, so a shifted line number is always caught): for a range, the
    excerpt is NOT a substring of the range without its first line, nor of the range without its last line;
  - a mode cite's mode is the one `git ls-tree` prints for that path at the commit, and its excerpt is the mode;
  - the path's last segment is not CONTRACT_NAME: a stage contract instructs the model and never catches a move
    (W4F1-3).
  A `claude-and-codex` row's reach excerpt also holds DECIDE_CALL, and its reach cite is one of DECIDE_LINES, the
  envelope's own `decide(` call lines, each re-read at the commit (W4F1-3, W4F2-1).

THE READING LINES (fold 1, reading_problems): each of READING_LINES opens a bullet of "how to read it", and
STAGE_LINE names, as a backticked pair, every pair in STAGE_00_PAIRS and no other pair (W4F1-1). No
tasks/<name>.json exists for a name in DROPPED_ROWS (W4F1-4). A `caught` value is a reader's reading: it is
bound to its note's verdict word only, never to the code (W4F1-3, stated in the md).

THE NOTES (this lane's decision: the reading under the table is published too, so it is bound). Under
NOTES_HEADING there is one bullet per pair, opening with the pair's name in bold; its last verdict word (a
backticked CAUGHT_VALUES word) is that row's `caught`; and every line reference in it (a backticked
`<file>:<n>` or `<file>:<lo>-<hi>`, a bare `<n>` or `<lo>-<hi>` meaning the file named before it in the same
bullet, a short path read under NOTE_DEFAULT_ROOT unless it starts with a NOTE_ROOTS key) lies inside its
file at the commit. NOTE_REFS pins how many references are read, so a parser that reads none is red.

THE FORWARD BINDING (for the per-task lanes, CP4). Every `tasks/*.json` present in the study folder needs a
row named by its stem. With none present today the clause reads zero, and TheForwardBinding shows it fires on
a planted task in a temporary folder first.

HISTORY. Every git read goes through git(); outside a work tree, in a shallow clone, or with a commit absent
it raises, so the test errors loudly and never skips.

Mutants (each asserted red, in memory): drop a row; double a row; a pair outside the list; the dropped mark
moved; a tasks/declarations.json planted; a codex reach cite that is no decide( call; a stage contract
cited; a stage 00 pair cut from the stage line, or another pair added to it; a reading line removed; shift a line number; change a reach value, outside the vocabulary and inside it; break the `none` rule both ways; put a value other than
DASH in a `reach where` or `reach excerpt` cell of a `none` row; swap an excerpt between rows; give a mode cite
the wrong mode; cite a path absent at the commit, a range outside the file, a non-gars path; point the commit,
substituted in memory, at ANCESTOR_MUTANT (an ancestor of the round 4 base whose `gars/` tree differs from
COMMIT's in 205 files); and narrow each named constant through this module's own globals.

No model, no network, stdlib only.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

STUDY_DIR = Path(__file__).resolve().parent.parent
REPO = STUDY_DIR.parent.parent
if str(STUDY_DIR) not in sys.path:
    sys.path.insert(0, str(STUDY_DIR))

THIS = sys.modules[__name__]

TABLE = STUDY_DIR / "coverage_today.md"
TASKS_DIR = STUDY_DIR / "tasks"

# glitch-f3's ruling 1: the 6 Oct commit, and main at 15:00 EDT that day, whose gars/ tree is the same.
COMMIT = "a626cdc2337246e972a198b026d53ce836416321"
SAME_GARS_AS = "0f602ea0b991cd3c85f361fc625cec21cfd9dbc1"
# The in-memory commit mutant: an ancestor of the base whose gars/ diff against COMMIT is 205 files.
ANCESTOR_MUTANT = "844a4ce"
ANCESTOR_GARS_DIFF = 205

# The plan's table of ten pairs, the dropped unprompted confound left out.
PAIRS = (
    "scope-read",
    "template-adherence",
    "number-fidelity",
    "precondition-refusal",
    "plan-gate",
    "confounded-design",
    "declarations",
    "explain-not-act",
    "approval-scope",
    "conditional-yes",
)
DROPPED = "confounded-design-unprompted"
DROPPED_ROWS = ("declarations",)
DROPPED_MARK = " (dropped)"  # W4F1-4 (the lane lead's decision): glitch-f3 dropped declarations from round 4

COLUMNS = ("pair", "trap's wrong move", "caught", "where", "excerpt", "reach", "reach where", "reach excerpt")
CAUGHT_VALUES = ("yes", "no", "partly")
CAUGHT_NO = "no"
# glitch-f3's ruling 2: the reach column's closed values, plus REACH_NONE exactly when caught is no.
REACH_VALUES = ("claude-only", "claude-and-codex", "every-agent")
REACH_NONE = "none"
DASH = "-"
CITED_ROOT = "gars/"
CONTRACT_NAME = "CONTEXT.md"  # W4F1-3: a stage contract instructs the model; it is never what catches a move
DECIDE_CALL = "decide("       # W4F1-3: a claude-and-codex reach cite is a call of guard_hook.decide
# W4F2-1 (the lane lead's decision): the only claude-and-codex reach cites, the envelope's own decide( call lines at
# COMMIT; decide_line_problems re-reads each and requires its first line, stripped, to open with DECIDE_CALL.
DECIDE_LINES = ("gars/_system/codex_hook.py:323", "gars/_system/codex_hook.py:378",
                "gars/_system/codex_hook.py:416-417", "gars/_system/codex_hook.py:426")
STAGE_00_PAIRS = ("scope-read", "template-adherence", "number-fidelity", "approval-scope", "conditional-yes")  # W4F1-1
# The "how to read it" lines fold 1 added (W4F1-1, -2, -3); the first names every stage 00 pair and no other pair.
READING_LINES = ("Each row's stage.", "Reach is the weakest.", "A verdict is a reading.")
STAGE_LINE = READING_LINES[0]
# Where each reach lives (glitch-f3's ruling 2, as the md defines it).
CLAUDE_HOMES = ("gars/.claude/",)
CODEX_HOMES = ("gars/_system/codex_hook.py", "gars/.codex/")
DECIDE_FILES = ("gars/_system/guard_hook.py", "gars/_system/tools/policy.py", "gars/_system/tools/registry.json",
                "gars/_system/tools/closed_output.py")

CITE = re.compile(r"(?P<path>[^\s:@]+)(?::(?P<lo>[1-9][0-9]*)(?:-(?P<hi>[1-9][0-9]*))?|@(?P<mode>[0-7]{6}))\Z")
SEPARATOR_CELL = re.compile(r":?-{3,}:?\Z")
# The notes under the table (each row's reading in two lines), bound too.
NOTES_HEADING = "## Why each row reads as it does"
NOTE_NAME = re.compile(r"- \*\*(?P<name>[a-z-]+(?: \(dropped\))?)\.\*\*")
NOTE_CITE = re.compile(r"(?P<path>[A-Za-z0-9_./-]+\.(?:py|json|toml|md)):(?P<lo>[1-9][0-9]*)(?:-(?P<hi>[1-9][0-9]*))?")
NOTE_MORE = re.compile(r"(?P<lo>[1-9][0-9]*)(?:-(?P<hi>[1-9][0-9]*))?")
NOTE_ROOTS = {".claude/": "gars/", ".codex/": "gars/"}
NOTE_DEFAULT_ROOT = "gars/_system/"
NOTE_REFS = 47  # the notes' line references, counted by note_refs; a change to the notes re-counts them


class GitError(RuntimeError):
    """A git read that could not be made: never a skip, never a pass."""


def git(*args: str) -> str:
    proc = subprocess.run(["git", "-C", str(REPO), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.decode('utf-8', 'replace')[:300]}")
    return proc.stdout.decode("utf-8")


_CACHE: dict[tuple[str, ...], str] = {}


def git_at(*args: str) -> str:
    """git() for reads of fixed objects (a sha's tree, blobs, log, diff), cached per run. require_history()
    and every check that must see the live repository call git() itself, uncached."""
    if args not in _CACHE:
        _CACHE[args] = git(*args)
    return _CACHE[args]


def require_history() -> None:
    """Outside a work tree, or in a shallow clone, the pins cannot be read: fail loudly."""
    if git("rev-parse", "--is-inside-work-tree").strip() != "true":
        raise GitError("not inside a git work tree")
    if git("rev-parse", "--is-shallow-repository").strip() != "false":
        raise GitError("a shallow clone: the 6 Oct commit and its comparisons need full history")


class Tree:
    """Files and modes at one commit, read with git show and git ls-tree, cached."""

    def __init__(self, commit: str):
        require_history()
        self.commit = commit
        self._text: dict[str, str | None] = {}
        self._entry: dict[str, tuple[str, str] | None] = {}

    def entry(self, path: str) -> tuple[str, str] | None:
        """(mode, type) of path at the commit, or None when absent."""
        if path not in self._entry:
            out = git_at("ls-tree", self.commit, "--", path)
            found = None
            for line in out.splitlines():
                meta, _, name = line.partition("\t")
                if name == path:
                    mode, kind, _ = meta.split(" ")
                    found = (mode, kind)
            self._entry[path] = found
        return self._entry[path]

    def text(self, path: str) -> str | None:
        if path not in self._text:
            entry = self.entry(path)
            self._text[path] = git_at("show", f"{self.commit}:{path}") if entry and entry[1] == "blob" else None
        return self._text[path]


def file_lines(text: str) -> list[str]:
    """The file's lines as git and an editor number them: split at "\\n" only (str.splitlines() also splits
    at form feeds and Unicode line separators, which would shift every later line number)."""
    lines = text.split("\n")
    return lines[:-1] if lines and lines[-1] == "" else lines


def normalise(text: str) -> str:
    return " ".join(text.split())


def unwrap(cell: str) -> str:
    if len(cell) >= 2 and cell.startswith("`") and cell.endswith("`"):
        return cell[1:-1]
    return cell


def split_row(line: str) -> list[str] | None:
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|") and not s.endswith("\\|")) or len(s) < 2:
        return None
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s[1:-1])]


def parse(text: str) -> tuple[list[dict[str, str]], list[str]]:
    """The table's rows as {column: cell} (backticks unwrapped), and the shape problems."""
    problems: list[str] = []
    lines = text.splitlines()
    table = [i for i, line in enumerate(lines) if line.lstrip().startswith("|")]
    if not table:
        return [], ["no table"]
    if table != list(range(table[0], table[0] + len(table))):
        problems.append("more than one table: the lines starting with | are not contiguous")
    header = split_row(lines[table[0]])
    if header is None or tuple(header) != COLUMNS:
        problems.append(f"the header is not exactly {' | '.join(COLUMNS)}")
        return [], problems
    if len(table) < 2 or not all(SEPARATOR_CELL.match(c or "") for c in (split_row(lines[table[1]]) or [""])) \
            or len(split_row(lines[table[1]]) or []) != len(COLUMNS):
        problems.append("the header's separator row is missing or malformed")
        return [], problems
    rows = []
    for i in table[2:]:
        cells = split_row(lines[i])
        if cells is None or len(cells) != len(COLUMNS):
            problems.append(f"line {i + 1}: not a row of {len(COLUMNS)} cells")
            continue
        rows.append({col: unwrap(cell) for col, cell in zip(COLUMNS, cells)})
    return rows, problems


def cite_problems(tree: Tree, cite: str, excerpt: str, label: str) -> list[str]:
    m = CITE.match(cite)
    if not m:
        return [f"{label}: {cite!r} is not path:line, path:lo-hi or path@mode"]
    path = m["path"]
    if not path.startswith(CITED_ROOT) or ".." in path.split("/"):
        return [f"{label}: {path} is not a path under {CITED_ROOT}"]
    if path.rsplit("/", 1)[-1] == CONTRACT_NAME:
        return [f"{label}: {path} is a stage contract, an instruction to the model, never a guard"]
    entry = tree.entry(path)
    if entry is None or entry[1] != "blob":
        return [f"{label}: {path} is not a file at {tree.commit}"]
    if m["mode"]:
        out = []
        if entry[0] != m["mode"]:
            out.append(f"{label}: {path} has mode {entry[0]} at {tree.commit}, not {m['mode']}")
        if excerpt != m["mode"]:
            out.append(f"{label}: a mode cite's excerpt is the mode, not {excerpt!r}")
        return out
    lo = int(m["lo"])
    hi = int(m["hi"] or lo)
    if hi < lo:
        return [f"{label}: range {lo}-{hi} runs backwards"]
    lines = file_lines(tree.text(path) or "")
    if hi > len(lines):
        return [f"{label}: {path}:{lo}-{hi} is outside the file ({len(lines)} lines at {tree.commit})"]
    want = normalise(excerpt)
    if not want or want == DASH:
        return [f"{label}: the excerpt is empty"]
    cited = lines[lo - 1:hi]
    if want not in normalise(" ".join(cited)):
        return [f"{label}: the excerpt is not in {path}:{lo}-{hi} at {tree.commit}"]
    if hi > lo and (want in normalise(" ".join(cited[1:])) or want in normalise(" ".join(cited[:-1]))):
        return [f"{label}: the cite {path}:{lo}-{hi} is not tight (the excerpt fits without its first or last line)"]
    return []


def task_problems(names: set[str], tasks_dir: Path) -> tuple[list[str], int]:
    """(problems, tasks seen): every tasks/*.json needs a row named by its stem."""
    tasks = sorted(tasks_dir.glob("*.json")) if tasks_dir.is_dir() else []
    return [f"tasks/{t.name} has no row" for t in tasks if t.stem not in names], len(tasks)


def pin_problems(commit: str) -> list[str]:
    """The commit resolves to COMMIT (the full sha of the 6 Oct commit; W4F1-5: that one equality covers the
    full-sha and date clauses this function once also held), and its gars/ tree is SAME_GARS_AS's."""
    require_history()
    out = []
    full = git_at("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
    if full != COMMIT:
        out.append(f"the commit {commit} is not the pinned 6 Oct commit {COMMIT}")
    if git_at("diff", "--name-only", SAME_GARS_AS, full, "--", "gars").strip():
        out.append(f"the gars/ tree at {commit} differs from {SAME_GARS_AS}'s")
    return out


def cited_path(cite: str) -> str:
    m = CITE.match(cite)
    return m["path"] if m else ""


def home_problems(reach: str, where: str, reach_where: str, label: str) -> list[str]:
    """A reach value is bound to where its two cites live (the md's own definitions): claude-only, both under
    gars/.claude/; claude-and-codex, the guard in a file `decide` reads (DECIDE_FILES) and the reach cite in Codex's
    envelope (CODEX_HOMES); every-agent, neither cite in any of those nor under gars/.claude/."""
    w, r = cited_path(where), cited_path(reach_where)
    under = lambda path, homes: any(path == h or (h.endswith("/") and path.startswith(h)) for h in homes)
    harness = CLAUDE_HOMES + CODEX_HOMES + DECIDE_FILES
    ok = {"claude-only": under(w, CLAUDE_HOMES) and under(r, CLAUDE_HOMES),
          "claude-and-codex": under(w, DECIDE_FILES) and under(r, CODEX_HOMES),
          "every-agent": not under(w, harness) and not under(r, harness)}.get(reach, True)
    return [] if ok else [f"{label}: reach {reach!r} does not match where its cites live ({w}, {r})"]


def note_bullets(text: str) -> list[str]:
    """The bullets of the NOTES_HEADING section, each joined into one string."""
    lines = text.splitlines()
    if NOTES_HEADING not in lines:
        return []
    bullets: list[str] = []
    for line in lines[lines.index(NOTES_HEADING) + 1:]:
        if line.startswith("## "):
            break
        if line.startswith("- "):
            bullets.append(line)
        elif line.startswith("  ") and bullets:
            bullets[-1] += " " + line.strip()
    return bullets


def note_refs(bullet: str) -> list[tuple[str, int, int]]:
    """(repo path, lo, hi) for every line reference in one note bullet."""
    found, path = [], None
    for span in re.findall(r"`([^`]+)`", bullet):
        full, more = NOTE_CITE.fullmatch(span), NOTE_MORE.fullmatch(span)
        if full:
            short = full["path"]
            root = next((r for k, r in NOTE_ROOTS.items() if short.startswith(k)), NOTE_DEFAULT_ROOT)
            path, lo, hi = root + short, full["lo"], full["hi"]
        elif more and path:
            lo, hi = more["lo"], more["hi"]
        else:
            continue
        found.append((path, int(lo), int(hi or lo)))
    return found


def note_problems(text: str, caught: dict[str, str], tree: Tree) -> list[str]:
    """The notes under the table: one bullet per pair, named in bold first, whose last verdict word is the row's
    caught value; and every line reference in them inside its file at the commit (a bare `n` or `lo-hi` refers
    to the file named before it in the same bullet; a short path is under NOTE_DEFAULT_ROOT unless it starts with
    a key of NOTE_ROOTS)."""
    out: list[str] = []
    seen: list[str] = []
    for bullet in note_bullets(text):
        m = NOTE_NAME.match(bullet)
        if not m:
            out.append(f"note {bullet[:40]!r}: does not start with a bold pair name")
            continue
        name = m["name"].removesuffix(DROPPED_MARK)
        label = f"note ({name})"
        if name not in PAIRS or name in seen:
            out.append(f"{label}: outside the pair list or doubled")
        seen.append(name)
        spans = re.findall(r"`([^`]+)`", bullet)
        verdicts = [v for v in spans if v in CAUGHT_VALUES]
        if name in caught and (not verdicts or verdicts[-1] != caught[name]):
            out.append(f"{label}: its verdict {verdicts[-1:]} is not the row's caught value {caught[name]!r}")
        for path, lo, hi in note_refs(bullet):
            entry = tree.entry(path)
            if entry is None or entry[1] != "blob":
                out.append(f"{label}: {path} is not a file at {tree.commit}")
                continue
            n = len(file_lines(tree.text(path) or ""))
            if hi < lo or hi > n:
                out.append(f"{label}: {path}:{lo}-{hi} is outside the file ({n} lines) or runs backwards")
    for name in PAIRS:
        if name not in seen:
            out.append(f"{name} has no note")
    return out


def decide_line_problems(tree: Tree) -> list[str]:
    """Each of DECIDE_LINES is a statement that calls decide (its first cited line, stripped, opens with
    DECIDE_CALL), never a docstring or comment line that mentions it (W4F2-1)."""
    out = []
    for cite in DECIDE_LINES:
        m = CITE.match(cite)
        lines = file_lines(tree.text(m["path"]) or "") if m and not m["mode"] else []
        lo = int(m["lo"]) if m and m["lo"] else 0
        if not (0 < lo <= len(lines)) or not lines[lo - 1].strip().startswith(DECIDE_CALL):
            out.append(f"{cite} is not a {DECIDE_CALL} call line at {tree.commit}")
    return out


def reading_line(text: str, head: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"- **{head}**"):
            return line
    return ""


def reading_problems(text: str) -> list[str]:
    """Fold 1's reading lines (W4F1-1 to -3): each of READING_LINES is present, and STAGE_LINE names, as a
    backticked pair, every pair in STAGE_00_PAIRS (each one in PAIRS) and no other pair."""
    out = [f"the reading line {head!r} is missing" for head in READING_LINES if not reading_line(text, head)]
    named = set(re.findall(r"`([a-z-]+)`", reading_line(text, STAGE_LINE))) & set(PAIRS)
    for pair in STAGE_00_PAIRS:
        if pair not in PAIRS:
            out.append(f"the stage 00 pair {pair} is outside the pair list")
        elif pair not in named:
            out.append(f"the stage line does not name the stage 00 pair {pair}")
    out += [f"the stage line names {pair}, which is not a stage 00 pair" for pair in sorted(named - set(STAGE_00_PAIRS))]
    return out


def problems(text: str, commit: str = COMMIT, tasks_dir: Path = TASKS_DIR) -> list[str]:
    """Every problem with the table, read against the commit. Empty means the table is bound."""
    rows, out = parse(text)
    out = out + pin_problems(commit)
    tree = Tree(commit)
    seen: list[str] = []
    for n, row in enumerate(rows, 1):
        pair = row["pair"]
        marked = pair.endswith(DROPPED_MARK)
        name = pair[:-len(DROPPED_MARK)] if marked else pair
        label = f"row {n} ({name})"
        if name not in PAIRS:
            out.append(f"{label}: {name!r} is outside the closed pair list")
        elif name in seen:
            out.append(f"{label}: {name} is doubled")
        seen.append(name)
        if name in DROPPED_ROWS and not marked:
            out.append(f"{label}: the dropped row {name} is not marked{DROPPED_MARK}")
        if marked and name not in DROPPED_ROWS:
            out.append(f"{label}: {name} is marked dropped but is not")
        if not row["trap's wrong move"] or row["trap's wrong move"] == DASH:
            out.append(f"{label}: the trap's wrong move is empty")
        caught, reach = row["caught"], row["reach"]
        if caught not in CAUGHT_VALUES:
            out.append(f"{label}: caught {caught!r} is outside {CAUGHT_VALUES}")
        if reach not in REACH_VALUES and reach != REACH_NONE:
            out.append(f"{label}: reach {reach!r} is outside {REACH_VALUES} and {REACH_NONE!r}")
        if (reach == REACH_NONE) != (caught == CAUGHT_NO):
            out.append(f"{label}: reach is {REACH_NONE!r} exactly when caught is {CAUGHT_NO!r} (caught {caught!r}, reach {reach!r})")
        out += cite_problems(tree, row["where"], row["excerpt"], f"{label} where")
        if reach == REACH_NONE:
            for col in ("reach where", "reach excerpt"):
                if row[col] != DASH:
                    out.append(f"{label}: {col} of a {REACH_NONE!r} row is {row[col]!r}, not {DASH!r}")
        else:
            out += cite_problems(tree, row["reach where"], row["reach excerpt"], f"{label} reach where")
            out += home_problems(reach, row["where"], row["reach where"], label)
            if reach == "claude-and-codex" and DECIDE_CALL not in row["reach excerpt"]:
                out.append(f"{label}: a claude-and-codex reach excerpt is a {DECIDE_CALL} call in Codex's envelope")
            if reach == "claude-and-codex" and row["reach where"] not in DECIDE_LINES:
                out.append(f"{label}: reach where {row['reach where']} is not one of the envelope's decide( call lines")
    out += decide_line_problems(tree)
    for name in PAIRS:
        if name not in seen:
            out.append(f"{name} has no row")
    out += task_problems(set(seen), tasks_dir)[0]
    out += [f"tasks/{name}.json is a dropped pair's task" for name in DROPPED_ROWS
            if (tasks_dir / f"{name}.json").exists()]
    caught = {r["pair"].removesuffix(DROPPED_MARK): r["caught"] for r in rows}
    out += note_problems(text, caught, tree)
    out += reading_problems(text)
    return out


# --- mutation helpers (in memory only) -------------------------------------------------------------------------

def table_text() -> str:
    return TABLE.read_text(encoding="utf-8")


def row_lines(text: str) -> list[int]:
    lines = text.splitlines()
    table = [i for i, line in enumerate(lines) if line.lstrip().startswith("|")]
    return table[2:]


def cell_of(text: str, index: int, col: str) -> str:
    lines = text.splitlines()
    return split_row(lines[row_lines(text)[index]])[COLUMNS.index(col)]


def with_cell(text: str, index: int, col: str, value: str) -> str:
    lines = text.splitlines()
    at = row_lines(text)[index]
    cells = re.split(r"(?<!\\)\|", lines[at].strip()[1:-1])
    cells[COLUMNS.index(col)] = " " + value.replace("|", "\\|") + " "
    lines[at] = "|" + "|".join(cells) + "|"
    return "\n".join(lines) + "\n"


def without_row(text: str, index: int) -> str:
    lines = text.splitlines()
    del lines[row_lines(text)[index]]
    return "\n".join(lines) + "\n"


def with_row_doubled(text: str, index: int) -> str:
    lines = text.splitlines()
    at = row_lines(text)[index]
    lines.insert(at + 1, lines[at])
    return "\n".join(lines) + "\n"


def index_of(text: str, pair: str) -> int:
    for i in range(len(row_lines(text))):
        name = unwrap(cell_of(text, i, "pair"))
        if name == pair or name == pair + DROPPED_MARK:
            return i
    raise KeyError(pair)


def shifted(cite: str, by: int) -> str:
    m = CITE.match(unwrap(cite))
    if not m or m["mode"]:
        return cite
    lo = int(m["lo"]) + by
    hi = int(m["hi"] or m["lo"]) + by
    return f"`{m['path']}:{lo}`" if lo == hi else f"`{m['path']}:{lo}-{hi}`"


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = table_text()

    def assertRed(self, text, needle, **kw):
        found = problems(text, **kw)
        self.assertTrue(any(needle in p for p in found), f"expected a problem with {needle!r}, got {found}")


class TheTable(Base):
    def test_the_table_is_bound_to_the_commit(self):
        self.assertEqual(problems(self.text), [])

    def test_one_row_per_pair_and_nothing_else(self):
        rows, shape = parse(self.text)
        self.assertEqual(shape, [])
        names = [r["pair"].removesuffix(DROPPED_MARK) for r in rows]
        self.assertEqual(sorted(names), sorted(PAIRS))
        self.assertEqual(len(rows), len(PAIRS))

    def test_the_closed_lists(self):
        self.assertEqual(len(PAIRS), 10)
        self.assertEqual(len(set(PAIRS)), 10)
        self.assertNotIn(DROPPED, PAIRS)
        self.assertTrue(set(DROPPED_ROWS) <= set(PAIRS))
        self.assertEqual(CAUGHT_VALUES, ("yes", "no", "partly"))
        self.assertIn(CAUGHT_NO, CAUGHT_VALUES)

    def test_the_dropped_row_is_marked(self):
        rows, _ = parse(self.text)
        marked = [r["pair"] for r in rows if r["pair"].endswith(DROPPED_MARK)]
        self.assertEqual(marked, [c + DROPPED_MARK for c in DROPPED_ROWS])


class ThePin(Base):
    def test_the_pinned_commit_is_the_6_oct_commit(self):
        self.assertEqual(pin_problems(COMMIT), [])
        self.assertEqual(git("log", "-1", "--format=%H %cI", COMMIT).split()[0], COMMIT)

    def test_the_gars_diff_against_the_15_00_main_is_empty(self):
        self.assertEqual(git("diff", "--name-only", SAME_GARS_AS, COMMIT, "--", "gars").strip(), "")

    def test_a_shallow_clone_or_no_git_fails_loudly(self):
        real = subprocess.run

        def shallow(cmd, *a, **k):
            if "--is-shallow-repository" in cmd:
                return subprocess.CompletedProcess(cmd, 0, b"true\n", b"")
            return real(cmd, *a, **k)

        with mock.patch.object(subprocess, "run", shallow):
            with self.assertRaises(GitError):
                problems(self.text)

        def no_git(cmd, *a, **k):
            return subprocess.CompletedProcess(cmd, 128, b"", b"fatal: not a git repository")

        with mock.patch.object(subprocess, "run", no_git):
            with self.assertRaises(GitError):
                problems(self.text)

    def test_mutant_commit_pointed_at_the_ancestor_goes_red(self):
        full = git("rev-parse", "--verify", f"{ANCESTOR_MUTANT}^{{commit}}").strip()
        git("merge-base", "--is-ancestor", full, "HEAD")
        diff = git("diff", "--name-only", full, COMMIT, "--", "gars").split()
        self.assertEqual(len(diff), ANCESTOR_GARS_DIFF)
        for commit in (ANCESTOR_MUTANT, full):
            found = problems(self.text, commit=commit)
            self.assertTrue(any("is not the pinned 6 Oct commit" in p for p in found), found)
            self.assertTrue(any("differs from" in p for p in found), found)
            self.assertTrue(any(" where:" in p for p in found), f"no cite went red at {commit}: {found}")

    def test_mutant_commit_constant_substituted_goes_red(self):
        full = git("rev-parse", "--verify", f"{ANCESTOR_MUTANT}^{{commit}}").strip()
        with mock.patch.object(THIS, "COMMIT", full):
            found = problems(self.text, commit=full)
        self.assertTrue(any("differs from" in p for p in found), found)
        self.assertTrue(any(" where:" in p for p in found), found)


class TheRows(Base):
    def test_mutant_drop_each_row(self):
        for i, pair in enumerate(PAIRS):
            with self.subTest(pair=pair):
                self.assertRed(without_row(self.text, index_of(self.text, pair)), f"{pair} has no row")

    def test_mutant_double_a_row(self):
        self.assertRed(with_row_doubled(self.text, 0), "is doubled")

    def test_mutant_a_pair_outside_the_list(self):
        self.assertRed(with_cell(self.text, index_of(self.text, "confounded-design"), "pair", DROPPED),
                       "outside the closed pair list")

    def test_mutant_dropped_mark_moved(self):
        d = index_of(self.text, "declarations")
        self.assertRed(with_cell(self.text, d, "pair", "declarations"), "is not marked")
        self.assertRed(with_cell(self.text, 0, "pair", unwrap(cell_of(self.text, 0, "pair")) + DROPPED_MARK),
                       "is marked dropped but is not")

    def test_mutant_empty_wrong_move(self):
        self.assertRed(with_cell(self.text, 0, "trap's wrong move", DASH), "wrong move is empty")

    def test_mutant_header_and_second_table(self):
        self.assertRed(self.text.replace("| reach excerpt |", "| reach note |", 1), "the header is not exactly")
        self.assertRed(self.text + "\nnote\n\n| a | b |\n", "more than one table")
        lines = self.text.splitlines()
        at = row_lines(self.text)[0]
        lines[at] = lines[at] + " an extra cell |"
        self.assertRed("\n".join(lines) + "\n", "not a row of")


class TheValues(Base):
    def test_mutant_caught_outside_its_set(self):
        self.assertRed(with_cell(self.text, 0, "caught", "maybe"), "is outside ('yes', 'no', 'partly')")

    def test_mutant_reach_value_changed(self):
        for i in range(len(PAIRS)):
            reach = cell_of(self.text, i, "reach")
            if reach == REACH_NONE:
                continue
            with self.subTest(row=i):
                self.assertRed(with_cell(self.text, i, "reach", "claude-and-gemini"), "is outside")

    def test_mutant_reach_value_swapped_inside_the_vocabulary(self):
        live = [i for i in range(len(PAIRS)) if cell_of(self.text, i, "reach") != REACH_NONE]
        self.assertTrue(live, "the table needs a live reach for this mutant to bite")
        # Fold 1 left every live row claude-and-codex, so each row is swapped to both other values; the
        # every-agent and claude-only homes are each also shown green on their own cites in test_home_rule_each_value.
        for i in live:
            for other in REACH_VALUES:
                if other == cell_of(self.text, i, "reach"):
                    continue
                with self.subTest(row=i, to=other):
                    self.assertRed(with_cell(self.text, i, "reach", other), "does not match where its cites live")

    def test_home_rule_each_value(self):
        self.assertEqual(home_problems("claude-only", "gars/.claude/settings.json:5", "gars/.claude/settings.json:3", "t"), [])
        self.assertTrue(home_problems("claude-only", "gars/_system/guard_hook.py:91", "gars/.claude/settings.json:3", "t"))
        self.assertEqual(home_problems("claude-and-codex", "gars/_system/tools/policy.py:156", "gars/.codex/hooks.json:9", "t"), [])
        self.assertTrue(home_problems("claude-and-codex", "gars/_system/stage00_register.py:513", "gars/_system/codex_hook.py:378", "t"))
        self.assertTrue(home_problems("claude-and-codex", "gars/_system/guard_hook.py:91", "gars/_system/stage00_register.py:513", "t"))
        self.assertEqual(home_problems("every-agent", "gars/_system/stage00_register.py:513", "gars/_system/stage00_register.py:863", "t"), [])
        self.assertTrue(home_problems("every-agent", "gars/_system/guard_hook.py:91", "gars/_system/stage00_register.py:863", "t"))
        self.assertTrue(home_problems("every-agent", "gars/_system/stage00_register.py:513", "gars/.codex/hooks.json:9", "t"))
        self.assertTrue(home_problems("every-agent", "gars/.claude/settings.json:83", "gars/_system/stage00_register.py:863", "t"))

    def test_mutant_reach_none_disagrees_with_caught(self):
        no = [i for i in range(len(PAIRS)) if cell_of(self.text, i, "caught") == CAUGHT_NO]
        yes = [i for i in range(len(PAIRS)) if cell_of(self.text, i, "caught") != CAUGHT_NO]
        self.assertTrue(no and yes, "the table needs both kinds of row for these mutants to bite")
        self.assertRed(with_cell(self.text, no[0], "caught", "partly"), "exactly when caught is")
        self.assertRed(with_cell(self.text, yes[0], "reach", REACH_NONE), "exactly when caught is")

    def test_mutant_reach_where_of_a_none_row_is_not_a_dash(self):
        no = [i for i in range(len(PAIRS)) if cell_of(self.text, i, "caught") == CAUGHT_NO][0]
        live = [i for i in range(len(PAIRS)) if cell_of(self.text, i, "caught") != CAUGHT_NO][0]
        cite, excerpt = cell_of(self.text, live, "reach where"), cell_of(self.text, live, "reach excerpt")
        self.assertRed(with_cell(self.text, no, "reach where", cite), "reach where of a 'none' row")
        self.assertRed(with_cell(self.text, no, "reach excerpt", excerpt), "reach excerpt of a 'none' row")
        self.assertRed(with_cell(self.text, no, "reach where", "--"), "reach where of a 'none' row")

    def test_named_constant_REACH_VALUES(self):
        self.assertEqual(REACH_VALUES, ("claude-only", "claude-and-codex", "every-agent"))
        self.assertNotIn(REACH_NONE, REACH_VALUES)
        used = {cell_of(self.text, i, "reach") for i in range(len(PAIRS))} - {REACH_NONE}
        for value in sorted(used):
            with self.subTest(dropped=value), \
                    mock.patch.object(THIS, "REACH_VALUES", tuple(v for v in REACH_VALUES if v != value)):
                self.assertTrue(any(f"reach {value!r} is outside" in p for p in problems(self.text)))

    def test_named_constant_REACH_NONE(self):
        self.assertEqual(REACH_NONE, "none")
        with mock.patch.object(THIS, "REACH_NONE", "nothing"):
            found = problems(self.text)
        self.assertTrue(any("reach 'none' is outside" in p for p in found), found)
        self.assertTrue(any("exactly when caught is" in p for p in found), found)

    def test_named_constant_CAUGHT_VALUES_and_CAUGHT_NO(self):
        used = {cell_of(self.text, i, "caught") for i in range(len(PAIRS))}
        for value in sorted(used):
            with self.subTest(dropped=value), \
                    mock.patch.object(THIS, "CAUGHT_VALUES", tuple(v for v in CAUGHT_VALUES if v != value)):
                self.assertTrue(any(f"caught {value!r} is outside" in p for p in problems(self.text)))
        with mock.patch.object(THIS, "CAUGHT_NO", "partly"):
            self.assertTrue(any("exactly when caught is" in p for p in problems(self.text)))

    def test_named_constants_PAIRS_and_DROPPED_ROWS(self):
        with mock.patch.object(THIS, "PAIRS", PAIRS[1:]):
            self.assertTrue(any("outside the closed pair list" in p for p in problems(self.text)))
        with mock.patch.object(THIS, "PAIRS", PAIRS + ("a-new-pair",)):
            self.assertTrue(any("a-new-pair has no row" in p for p in problems(self.text)))
        with mock.patch.object(THIS, "DROPPED_ROWS", ()):
            self.assertTrue(any("is marked dropped but is not" in p for p in problems(self.text)))


class TheCites(Base):
    def live_cites(self):
        for i in range(len(PAIRS)):
            yield i, "where", "excerpt"
            if cell_of(self.text, i, "reach") != REACH_NONE:
                yield i, "reach where", "reach excerpt"

    def test_every_answer_cites_a_gars_file_and_line(self):
        rows, _ = parse(self.text)
        for row in rows:
            for col in ("where",) + (("reach where",) if row["reach"] != REACH_NONE else ()):
                m = CITE.match(row[col])
                self.assertIsNotNone(m, row[col])
                self.assertTrue(m["path"].startswith(CITED_ROOT), row[col])

    def test_mutant_shift_each_line_number(self):
        for i, col, _ in self.live_cites():
            for by in (-1, 1):
                with self.subTest(row=i, col=col, by=by):
                    cite = cell_of(self.text, i, col)
                    self.assertRed(with_cell(self.text, i, col, shifted(cite, by)), f"{col}:")

    def test_mutant_swap_excerpts(self):
        n = len(PAIRS)
        for i in range(n):
            j = (i + 1) % n
            with self.subTest(row=i):
                self.assertRed(with_cell(self.text, i, "excerpt", cell_of(self.text, j, "excerpt")), "where:")

    def test_mutant_path_absent_range_outside_and_non_gars(self):
        cite = unwrap(cell_of(self.text, 0, "where"))
        path = CITE.match(cite)["path"]
        self.assertRed(with_cell(self.text, 0, "where", cite.replace(path, path + "x")), "is not a file at")
        self.assertRed(with_cell(self.text, 0, "where", f"{path}:99999"), "is outside the file")
        self.assertRed(with_cell(self.text, 0, "where", f"{path}:9-3"), "runs backwards")
        self.assertRed(with_cell(self.text, 0, "where", "docs/README.md:1"), "is not a path under")
        self.assertRed(with_cell(self.text, 0, "where", f"gars/../{path}:1"), "is not a path under")
        self.assertRed(with_cell(self.text, 0, "where", path), "is not path:line")

    def test_mutant_loose_range(self):
        for i, col, ex in self.live_cites():
            m = CITE.match(unwrap(cell_of(self.text, i, col)))
            if m["mode"]:
                continue
            lo, hi = int(m["lo"]), int(m["hi"] or m["lo"])
            with self.subTest(row=i, col=col):
                self.assertRed(with_cell(self.text, i, col, f"{m['path']}:{lo}-{hi + 1}"), "not tight")

    def test_mode_cite_right_and_wrong(self):
        tree = Tree(COMMIT)
        path = "gars/_system/stage00_register.py"
        mode = tree.entry(path)[0]
        self.assertEqual(mode, "100755")
        self.assertEqual(cite_problems(tree, f"{path}@{mode}", mode, "t"), [])
        wrong = "100644"
        self.assertTrue(any("has mode" in p for p in cite_problems(tree, f"{path}@{wrong}", wrong, "t")))
        self.assertTrue(any("excerpt is the mode" in p for p in cite_problems(tree, f"{path}@{mode}", "x", "t")))
        # The same, through the table: a row whose where becomes a mode cite.
        good = with_cell(with_cell(self.text, 0, "where", f"{path}@{mode}"), 0, "excerpt", mode)
        self.assertFalse(any("row 1" in p and " where:" in p for p in problems(good)), problems(good))
        bad = with_cell(with_cell(self.text, 0, "where", f"{path}@{wrong}"), 0, "excerpt", wrong)
        self.assertRed(bad, "has mode 100755")

    def test_lines_are_counted_at_newlines_only(self):
        tree = Tree(COMMIT)
        text = tree.text("gars/_system/codex_hook.py")
        self.assertEqual(len(file_lines(text)), text.count("\n"))
        self.assertNotEqual(len(file_lines(text)), len(text.splitlines()), "the guard needs a file where they differ")
        self.assertEqual(problems(self.text), [])
        with mock.patch.object(THIS, "file_lines", lambda t: t.splitlines()):
            self.assertTrue(any("codex_hook.py" in p for p in problems(self.text)))

    def test_whitespace_normalisation_is_the_stated_one(self):
        self.assertEqual(normalise("  a\n\t b  c "), "a b c")
        tree = Tree(COMMIT)
        path = "gars/.claude/settings.json"
        self.assertEqual(cite_problems(tree, f"{path}:3-5", "[ {", "t"),
                         ["t: the cite gars/.claude/settings.json:3-5 is not tight (the excerpt fits without its first or last line)"])
        self.assertEqual(cite_problems(tree, f"{path}:3-4", '"PreToolUse":\n[ {', "t"), [])
        self.assertTrue(cite_problems(tree, f"{path}:3-4", '"PreToolUse":[{', "t"))


class TheNotes(Base):
    def test_one_note_per_pair_bound_to_its_row(self):
        bullets = note_bullets(self.text)
        self.assertEqual(len(bullets), len(PAIRS))
        refs = [note_refs(b) for b in bullets]
        self.assertTrue(all(refs), "every note cites at least one line")
        self.assertEqual(sum(len(r) for r in refs), NOTE_REFS, "the notes' line references are all read (non-vacuity)")
        self.assertIn(("gars/_system/tools/registry.json", 555, 555), refs[[i for i, b in enumerate(bullets) if "explain-not-act" in b][0]])

    def test_mutant_note_reference_outside_its_file(self):
        self.assertIn("`guard_hook.py:957-962`", self.text)
        self.assertRed(self.text.replace("`guard_hook.py:957-962`", "`guard_hook.py:957-99999`", 1), "is outside the file")
        self.assertIn("`555`", self.text)
        self.assertRed(self.text.replace("`555`", "`55555`", 1), "tools/registry.json:55555-55555 is outside")
        self.assertRed(self.text.replace("`guard_hook.py:957-962`", "`guard_hooks.py:957-962`", 1), "is not a file at")
        self.assertRed(self.text.replace("`.claude/settings.json:83`", "`.claude/settings.json:9999`", 1), "gars/.claude/settings.json:9999")

    def test_mutant_note_verdict_or_bullet(self):
        at = self.text.index("- **number-fidelity.**")
        end = self.text.index("\n- **", at + 1)
        bullet = self.text[at:end]
        self.assertTrue(bullet.rstrip().endswith("`no`."))
        self.assertRed(self.text.replace(bullet, bullet.replace("`no`.", "`partly`."), 1), "is not the row's caught value")
        self.assertRed(self.text.replace(bullet + "\n", "", 1), "number-fidelity has no note")
        self.assertRed(self.text.replace("- **number-fidelity.**", "- **number fidelity.**", 1), "does not start with a bold pair name")
        self.assertRed(self.text.replace(NOTES_HEADING, "## Notes", 1), "has no note")


def bullet_of(text: str, pair: str) -> str:
    for b in note_bullets(text):
        if b.startswith(f"- **{pair}"):
            return b
    raise KeyError(pair)


class TheFold1(Base):
    """Lane review round 1 (W4F1-1 to W4F1-6), folded on the gap4 lane lead's decisions."""

    def test_w4f1_1_each_row_is_read_in_its_stage(self):
        line = reading_line(self.text, "Each row's stage.")
        self.assertTrue(line, "the reading rule names each row's stage")
        for pair in getattr(THIS, "STAGE_00_PAIRS", ()) or ("missing",):
            self.assertIn(f"`{pair}`", line)
        self.assertEqual(len(getattr(THIS, "STAGE_00_PAIRS", ())), 5)
        self.assertNotIn("The project is public.", self.text)
        self.assertNotIn("other project writes stay open", bullet_of(self.text, "template-adherence"))
        self.assertIn(("gars/_system/guard_hook.py", 796, 814), note_refs(bullet_of(self.text, "approval-scope")))
        self.assertIn(("gars/_system/guard_hook.py", 796, 814), note_refs(bullet_of(self.text, "template-adherence")))

    def test_w4f1_2_reach_is_the_weakest_guard_the_verdict_needs(self):
        self.assertTrue(reading_line(self.text, "Reach is the weakest."))
        i = index_of(self.text, "approval-scope")
        self.assertEqual(cell_of(self.text, i, "reach"), "claude-and-codex")
        self.assertTrue(unwrap(cell_of(self.text, i, "where")).startswith("gars/_system/guard_hook.py:"))
        self.assertIn(("gars/_system/stage00_register.py", 513, 514), note_refs(bullet_of(self.text, "approval-scope")))

    def test_w4f1_3_a_codex_reach_cite_is_a_decide_call(self):
        i = index_of(self.text, "scope-read")
        moved = with_cell(with_cell(self.text, i, "reach where", "gars/_system/codex_hook.py:15"), i, "reach excerpt",
                          "Codex blocks a call on exit 2 with a non-empty stderr")
        self.assertRed(moved, "decide(")
        self.assertEqual(getattr(THIS, "DECIDE_CALL", None), "decide(")

    def test_w4f1_3_no_cite_is_a_stage_contract(self):
        tree = Tree(COMMIT)
        found = cite_problems(tree, "gars/00_initialize_project/CONTEXT.md:1", "x", "t")
        self.assertTrue(any("stage contract" in p for p in found), found)
        self.assertTrue(reading_line(self.text, "A verdict is a reading."))

    def test_w4f1_4_declarations_is_dropped(self):
        i = index_of(self.text, "declarations")
        self.assertEqual(unwrap(cell_of(self.text, i, "pair")), "declarations (dropped)")
        self.assertIn("glitch-f3", bullet_of(self.text, "declarations"))
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "declarations.json").write_text("{}", encoding="utf-8")
            self.assertRed(self.text, "tasks/declarations.json is a dropped pair's task", tasks_dir=Path(tmp))
        self.assertFalse((TASKS_DIR / "declarations.json").exists())

    def test_w4f1_mutants_and_near_misses(self):
        tree = Tree(COMMIT)
        # DECIDE_CALL: the table's decide calls pass; the constant narrowed in memory turns them red.
        with mock.patch.object(THIS, "DECIDE_CALL", "decide_x("):
            self.assertTrue(any("reach excerpt is a decide_x( call" in p for p in problems(self.text)))
        # CONTRACT_NAME: a near-miss name is not a contract; the constant changed in memory lets a contract through.
        near = cite_problems(tree, "gars/00_initialize_project/MYCONTEXT.md:1", "x", "t")
        self.assertFalse(any("stage contract" in p for p in near), near)
        with mock.patch.object(THIS, "CONTRACT_NAME", "NOT-A-CONTRACT.md"):
            self.assertFalse(any("stage contract" in p for p in
                                 cite_problems(tree, "gars/00_initialize_project/CONTEXT.md:1", "x", "t")))
        self.assertRed(with_cell(self.text, index_of(self.text, "approval-scope"), "where",
                                 "gars/00_initialize_project/CONTEXT.md:1"), "is a stage contract")
        # STAGE_00_PAIRS and READING_LINES: each stage 00 pair cut from the stage line is red; a stage 01 pair
        # added to it is red; each constant widened in memory is red; each reading line removed is red.
        line = reading_line(self.text, STAGE_LINE)
        self.assertEqual(reading_problems(self.text), [])
        for pair in STAGE_00_PAIRS:
            with self.subTest(pair=pair):
                self.assertRed(self.text.replace(line, line.replace(f"`{pair}`", "a pair"), 1),
                               f"does not name the stage 00 pair {pair}")
        self.assertRed(self.text.replace(line, line + " `plan-gate`", 1), "names plan-gate, which is not a stage 00 pair")
        with mock.patch.object(THIS, "STAGE_00_PAIRS", STAGE_00_PAIRS + ("plan-gate",)):
            self.assertTrue(any("does not name the stage 00 pair plan-gate" in p for p in problems(self.text)))
        with mock.patch.object(THIS, "STAGE_00_PAIRS", STAGE_00_PAIRS + ("no-such-pair",)):
            self.assertTrue(any("no-such-pair is outside the pair list" in p for p in problems(self.text)))
        for head in READING_LINES:
            with self.subTest(head=head):
                gone = reading_line(self.text, head)
                self.assertRed(self.text.replace(gone + "\n", "", 1), f"the reading line {head!r} is missing")
        with mock.patch.object(THIS, "READING_LINES", READING_LINES + ("Not a line.",)):
            self.assertTrue(any("'Not a line.' is missing" in p for p in problems(self.text)))
        # The dropped task: a live pair's task is no dropped task; DROPPED_ROWS emptied lets a dropped one through.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "explain-not-act.json").write_text("{}", encoding="utf-8")
            self.assertEqual(problems(self.text, tasks_dir=Path(tmp)), [])
            (Path(tmp) / "declarations.json").write_text("{}", encoding="utf-8")
            with mock.patch.object(THIS, "DROPPED_ROWS", ()):
                self.assertFalse(any("dropped pair's task" in p for p in problems(self.text, tasks_dir=Path(tmp))))
        # W4F1-5: the pin is the rev-parse equality; a short sha of COMMIT resolves to it and passes, an ancestor fails.
        self.assertEqual(pin_problems(COMMIT[:8]), [])
        self.assertTrue(pin_problems(ANCESTOR_MUTANT))

    def test_w4f1_6_files_csv_mode(self):
        self.assertIn(("gars/_system/stage00_register.py", 679, 680),
                      note_refs(bullet_of(self.text, "precondition-refusal")))
        self.assertIn(("gars/_system/workspace.py", 107, 107), note_refs(bullet_of(self.text, "precondition-refusal")))
        self.assertIn("MACHINE_OWNED_MODE = 0o444", file_lines(Tree(COMMIT).text("gars/_system/workspace.py"))[106])


class TheFold2(Base):
    """Lane review round 2's MINOR (W4F2-1), folded on the gap4 lane lead's decision."""

    def test_w4f2_1_reach_cites_are_the_envelope_decide_calls(self):
        lines = getattr(THIS, "DECIDE_LINES", ())
        self.assertEqual(lines, ("gars/_system/codex_hook.py:323", "gars/_system/codex_hook.py:378",
                                 "gars/_system/codex_hook.py:416-417", "gars/_system/codex_hook.py:426"))
        self.assertEqual(decide_line_problems(Tree(COMMIT)), [])
        i = index_of(self.text, "approval-scope")
        doc = with_cell(with_cell(self.text, i, "reach where", "gars/_system/codex_hook.py:320"), i, "reach excerpt",
                        "decide()'s verdict with its refusal text kept")
        self.assertRed(doc, "is not one of the envelope's decide( call lines")
        # Mutant: the docstring line 320 admitted to DECIDE_LINES in memory is red, as a line that is no call.
        with mock.patch.object(THIS, "DECIDE_LINES", DECIDE_LINES + ("gars/_system/codex_hook.py:320",)):
            self.assertEqual(decide_line_problems(Tree(COMMIT)),
                             [f"gars/_system/codex_hook.py:320 is not a decide( call line at {COMMIT}"])


class TheForwardBinding(Base):
    def test_fires_on_a_planted_task_then_reads_the_real_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            planted = Path(tmp)
            (planted / "explain-not-act.json").write_text("{}", encoding="utf-8")
            (planted / "a-task-with-no-row.json").write_text("{}", encoding="utf-8")
            found, seen = task_problems(set(PAIRS), planted)
            self.assertEqual(seen, 2)
            self.assertEqual(found, ["tasks/a-task-with-no-row.json has no row"])
            self.assertRed(self.text, "a-task-with-no-row.json has no row", tasks_dir=planted)
            (planted / "a-task-with-no-row.json").unlink()
            self.assertEqual(problems(self.text, tasks_dir=planted), [])
        real = sorted(TASKS_DIR.glob("*.json")) if TASKS_DIR.is_dir() else []
        found, seen = task_problems(set(PAIRS), TASKS_DIR)
        self.assertEqual(seen, len(real))
        self.assertEqual(found, [])
        print(f"\ntest_coverage: tasks/*.json seen: {seen}", file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
