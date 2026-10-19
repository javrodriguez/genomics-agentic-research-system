#!/usr/bin/env python3
"""Each harness's own bookkeeping paths: what the end-state reader leaves out as the harness's, not the agent's.

    python3 evals/gap-study-4/harness_bookkeeping.py --check    the table's shape; exit 1 on any problem

ONE OF THE SEAM'S THREE TABLES (interface 8, glitch-f3's ruling, 6 Oct 2026). `agent_adapter.py` holds the adapters,
`transcript_view.py` the transcript parsers, and this module each harness's bookkeeping paths, all keyed by
`AgentAdapter.name`. A new harness adds one entry here and nothing else: no grader, task or manifest field changes.
`graders/endstate.py` takes the harness from the evidence (the take record's `agent.harness`) and asks `entry()`,
which refuses an unknown name and never defaults to any harness.

WHERE THE PATHS ARE. An entry holds two lists of patterns, each read for the take's own harness only:
    home_paths      relative to the take user's home folder as the evidence places it (the take record's `home`;
                    see `graders/endstate.py`): where a harness keeps its own bookkeeping.
    run_tree_paths  relative to the run tree: bookkeeping a harness leaves there itself, for example temp files
                    under TMPDIR, which round 3's driver points into the run tree (drive.py:172-182). The run tree
                    is where a task's right and wrong moves land, so a pattern here must be grounded and must hide
                    no task path (`endstate.exclusion_conflicts` checks it per task).
Under one harness, another harness's paths (of either list) are NOT excluded: an agent under one harness that writes
into another's folders made that change itself.

PATTERNS. `/`-separated segments. A segment is matched with `fnmatch.fnmatchcase` (so `*` never crosses a `/`); a
`**` segment matches zero or more whole segments. No leading `/`, no empty, `.` or `..` segment.

THE `claude-code` ENTRY, grounded in round 3's files only (the identical copy `drive.py`, and round 3's
pre-registration key `run_location.excluded_from_the_run_tree` at e2979b31). Excluded:

    .claude/projects/*/*.jsonl   the session file. drive.py:232-245 (`session_file`, the glob at 241-242): Claude Code writes it under
                                 `$CLAUDE_CONFIG_DIR`, or `~/.claude` when that is unset, as
                                 `projects/<folder>/<session id>.jsonl`. Round 3's isolation environment
                                 (drive.py:170, ISOLATION_ENV) sets no CLAUDE_CONFIG_DIR; whether an inherited one
                                 passes through is open (CP2).
    run_tree_paths: none         round 3's files ground no run-tree bookkeeping of Claude Code's own, so the list
                                 is empty until CP2 measures one (lane report w2a-cp3-endstate, open question 2).

NOT excluded, each recorded in the entry's `not_excluded` with its line (lane w2a's decisions):

    the auto-memory folder       drive.py:166-170: CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 turns it off. If it appears,
                                 something wrote it, and the reader shows it.
    .tmp/ (run tree)             drive.py:172-182: the take's temp folder (TMPDIR, TMP, TEMP). Every tool's scratch
                                 lands there, the agent's own included, so a placeholder data file written there is
                                 a created file. Not the harness's alone, so never excluded as a folder; a file
                                 Claude Code itself leaves there needs a grounded run_tree_paths pattern (CP2).
    data/staging/, .tmp/         drive.py:384-394: git-excluded in the checkout, which hides them from `git status`,
                                 never from the snapshots. data/staging/ is where the driver stages fixtures: an
                                 operator write, matched to its logged event like any other.
    excluded_from_the_run_tree   drive.py:330-332 and round 3's prereg key: paths the checkout leaves OUT of the
                                 run tree. They are absent there; anything that appears at one was written by
                                 someone in the take, so it is never excluded.

Anything else Claude Code may write in its home (round 3's files do not name it) is not excluded here; it is an
open question for CP2's box (lane report w2a-cp3-endstate).

VENDOR_CANDIDATES (lane vendor-admission T2) holds Codex's and Gemini's grounded candidates BESIDE the table: `entry()`
never reads them, so a codex or gemini take is still refused until a ruling promotes them after a real walk.

No model, no network, stdlib only.
"""

from __future__ import annotations

import fnmatch
import sys
from dataclasses import dataclass

# The Claude Code adapter's name, exactly (interface 8). This module, agent_adapter.py and transcript_view.py are
# the only modules that may type it.
CLAUDE_CODE = "claude-code"


@dataclass(frozen=True)
class Entry:
    """One harness's bookkeeping: the home-relative patterns excluded (at least one), the run-tree-relative ones
    (required, possibly empty), the lines that ground them, and what was considered and kept in (path, why)."""
    home_paths: tuple
    run_tree_paths: tuple
    grounds: tuple
    not_excluded: tuple


TABLE: dict = {
    CLAUDE_CODE: Entry(
        home_paths=(".claude/projects/*/*.jsonl",),
        run_tree_paths=(),
        grounds=(
            "evals/gap-study-4/drive.py:241-242 session_file: "
            "Path(os.environ.get(\"CLAUDE_CONFIG_DIR\") or (Path.home() / \".claude\")) / \"projects\", "
            "glob(f\"*/{session_id}.jsonl\")",
            "evals/gap-study-4/drive.py:170: ISOLATION_ENV sets no CLAUDE_CONFIG_DIR (it holds "
            "ENABLE_CLAUDEAI_MCP_SERVERS and CLAUDE_CODE_DISABLE_AUTO_MEMORY only); whether an inherited one passes "
            "through is open (CP2)",
            "run_tree_paths: none; round 3's files ground no run-tree bookkeeping of the harness's own (CP2 measures)",
        ),
        not_excluded=(
            ("auto-memory folder", "drive.py:166-170: CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 turns it off"),
            (".tmp/", "drive.py:172-182: the take's temp folder holds every tool's scratch, the agent's own included"),
            ("data/staging/", "drive.py:384-394: git-excluded only; the driver's staging, an operator write"),
            ("excluded_from_the_run_tree", "drive.py:330-332, round 3 prereg: absent from the run tree, so "
                                           "anything appearing there was written in the take"),
        ),
    ),
}


# VENDOR CANDIDATES (lane vendor-admission T2, glitch-b5, 16 Oct 2026). Codex's and Gemini's bookkeeping, grounded in
# this study's own files and held BESIDE the table, never in it: entry() never reads them, so production
# Evidence.load still refuses a codex or gemini take ("has no bookkeeping entry"). Their run_tree_paths hold the agent
# HOME alone (R4-4, glitch-26, lane vendor-b11 round 4: <run tree>/.home is snapshotted but not graded; arm A's HOME is
# outside the run tree). Nothing else in the run tree is grounded yet: what Codex and Gemini leave there shows only in
# a real walk's snapshots, and a guess would let harness furniture read as the agent's changes. Promotion into TABLE is
# a later ruling, after a real walk measures the run tree and before any regrade.json is committed (promotion changes
# regrade bytes).
# Their home_paths are inert in production today: the driver records the take's home as None and the sidecar
# snapshots only the run tree. tests/test_harness_bookkeeping.py VendorCandidates re-derives every pattern below.
VENDOR_CANDIDATES: dict = {
    "codex": Entry(
        home_paths=("sessions/**/rollout-*.jsonl",),
        run_tree_paths=(".home/**",),
        grounds=(
            "evals/gap-study-4/codex_adapter.py:41: rollout    `$CODEX_HOME/sessions/.../rollout-*.jsonl` (`...` any "
            "folders: sessions/<year>/<month>/<day>/ as native_snapshot.py:84 spells it)",
            "evals/gap-study-4/box/run_take.py:68 and 169-171: CONFIG_MOUNT = \"/opt/cfg\"; TAKE_ENV[CODEX] sets "
            "\"CODEX_HOME\": CONFIG_MOUNT, so the pattern is relative to CODEX_HOME, the config mount; since R-H5 "
            "(glitch-26, 19 Oct 2026) the row's \"HOME\" is RUN_TREE_HOME, the run tree's .home, so the home a "
            "codex take's evidence places these paths under is the config mount, not HOME",
            "run_tree_paths: .home/** (R4-4, glitch-26, lane vendor-b11 round 4): the agent HOME (R-H5's <run "
            "tree>/.home, box/run_take.py RUN_TREE_HOMEDIR) is inside the run tree, so the snapshots walk it "
            "(box/sidecar.py and the sidecar image stay byte-unchanged) but the end-state grader does not grade it; "
            "arm A's HOME is outside the run tree and its entry is untouched",
            "the rest of the run tree: unmeasured until a real walk (what Codex leaves there shows only in a "
            "walk's snapshots)",
        ),
        not_excluded=(
            (".tmp/", "box/run_take.py:93 and 153, 169-170: TMPDIR, TMP and TEMP point at the run tree's .tmp, which "
                      "holds every tool's scratch, the agent's own included; a file Codex itself leaves there needs a "
                      "pattern measured on a real walk"),
            ("the rest of CODEX_HOME", "box/run_take.py:169-171: the config mount also holds the login lease and "
                                       "Codex's other files; none is grounded as bookkeeping until a real walk"),
        ),
    ),
    "gemini": Entry(
        home_paths=(".gemini/tmp/*/chats/session-*.jsonl",),
        run_tree_paths=(".home/**",),
        grounds=(
            "evals/gap-study-4/native_snapshot.py:20: gemini_session_file reads under exactly "
            "<home>/.gemini/tmp/*/chats; native_snapshot.py:13: filename = session-<ISO minute>-<first 8 of the "
            "session id>.jsonl (or session-<minute>-<k>-<first 8>.jsonl)",
            "evals/gap-study-4/native_snapshot.py:16-18: assumed, not source-shown: the global temp dir is "
            "<home>/.gemini/tmp, and SANDBOX is not \"sandbox-exec\" (which would move it to <home>/.cache/.gemini)",
            "evals/gap-study-4/box/run_take.py:68 and 172-174, native_snapshot.py:9: homedir() is $GEMINI_CLI_HOME; "
            "TAKE_ENV[GEMINI] sets \"GEMINI_CLI_HOME\": CONFIG_MOUNT, so the pattern is relative to GEMINI_CLI_HOME, "
            "the config mount; since R-H5 (glitch-26, 19 Oct 2026) the row's \"HOME\" is RUN_TREE_HOME, the run "
            "tree's .home, so the home a gemini take's evidence places these paths under is the config mount, not "
            "HOME",
            "run_tree_paths: .home/** (R4-4, glitch-26, lane vendor-b11 round 4): the agent HOME (R-H5's <run "
            "tree>/.home, box/run_take.py RUN_TREE_HOMEDIR) is inside the run tree, so the snapshots walk it "
            "(box/sidecar.py and the sidecar image stay byte-unchanged) but the end-state grader does not grade it; "
            "arm A's HOME is outside the run tree and its entry is untouched",
            "the rest of the run tree: unmeasured until a real walk (what Gemini leaves there shows only in a "
            "walk's snapshots)",
        ),
        not_excluded=(
            (".tmp/", "box/run_take.py:93 and 153, 172-173: TMPDIR, TMP and TEMP point at the run tree's .tmp, which "
                      "holds every tool's scratch, the agent's own included; a file Gemini itself leaves there needs "
                      "a pattern measured on a real walk"),
            ("<chats>/<parent id>/<id>.jsonl", "native_snapshot.py:14-15: a subagent's session file, never matched "
                                               "by the pattern; unmeasured until a real walk"),
            (".gemini/tmp/<project>/ other entries", "lane note harness-window2-resume-2026-10-14.md: Gemini's tmp "
                                                     "folder may hold other entries a live walk shows; open"),
        ),
    ),
}

class UnknownHarness(ValueError):
    """A harness name this table holds no entry for (or no name at all). Never defaulted."""


def entry(name, table: dict | None = None) -> Entry:
    """The bookkeeping entry for `name`, or UnknownHarness. There is no default harness."""
    table = TABLE if table is None else table
    if not isinstance(name, str) or not name:
        raise UnknownHarness(f"no harness named (got {name!r}); the evidence must name one, never defaulted")
    if name not in table:
        raise UnknownHarness(f"harness {name!r} has no bookkeeping entry (known: {sorted(table)})")
    return table[name]


def pattern_problems(pattern) -> list[str]:
    if not isinstance(pattern, str) or not pattern:
        return [f"pattern {pattern!r} is not a non-empty string"]
    if pattern.startswith("/"):
        return [f"pattern {pattern!r} is absolute"]
    if any(seg in ("", ".", "..") for seg in pattern.split("/")):
        return [f"pattern {pattern!r} has an empty, '.' or '..' segment"]
    if pattern.split("/")[0] == "**" and len(pattern.split("/")) == 1:
        return [f"pattern {pattern!r} would exclude everything"]
    return []


def matches(pattern: str, path: str) -> bool:
    """Does `path` (relative, `/`-separated) match `pattern` (see PATTERNS)?"""
    return _match(pattern.split("/"), path.split("/"))


def _match(pat: list, segs: list) -> bool:
    if not pat:
        return not segs
    if pat[0] == "**":
        return any(_match(pat[1:], segs[i:]) for i in range(len(segs) + 1))
    return bool(segs) and fnmatch.fnmatchcase(segs[0], pat[0]) and _match(pat[1:], segs[1:])


def excluded(name, home_path: str, table: dict | None = None) -> bool:
    """Is `home_path` (relative to the take user's home) the bookkeeping of harness `name`? Only that harness's
    entry is read."""
    return any(matches(p, home_path) for p in entry(name, table).home_paths)


def run_tree_excluded(name, run_path: str, table: dict | None = None) -> bool:
    """Is `run_path` (relative to the run tree) bookkeeping harness `name` leaves in the run tree itself? Only that
    harness's entry is read."""
    return any(matches(p, run_path) for p in entry(name, table).run_tree_paths)


def check_table(table: dict | None = None) -> list[str]:
    table = TABLE if table is None else table
    problems = []
    if not isinstance(table, dict) or not table:
        return ["the table must be a non-empty dict keyed by AgentAdapter.name"]
    for name, e in table.items():
        if not isinstance(name, str) or not name:
            problems.append(f"key {name!r} is not a harness name")
        if not isinstance(e, Entry):
            problems.append(f"{name}: not an Entry")
            continue
        if not isinstance(e.home_paths, tuple) or not e.home_paths:
            problems.append(f"{name}: home_paths must be a non-empty tuple")
        else:
            for p in e.home_paths:
                problems += [f"{name}: {x}" for x in pattern_problems(p)]
        if not isinstance(e.run_tree_paths, tuple):
            problems.append(f"{name}: run_tree_paths must be a tuple (empty when the harness leaves none)")
        else:
            for p in e.run_tree_paths:
                problems += [f"{name}: run tree: {x}" for x in pattern_problems(p)]
        if not isinstance(e.grounds, tuple) or not e.grounds or not all(isinstance(g, str) and g for g in e.grounds):
            problems.append(f"{name}: every entry names its grounds")
        if not isinstance(e.not_excluded, tuple) or not all(
                isinstance(x, tuple) and len(x) == 2 and all(isinstance(s, str) and s for s in x) for x in e.not_excluded):
            problems.append(f"{name}: not_excluded is a tuple of (path, why)")
    if CLAUDE_CODE not in table:
        problems.append(f"{CLAUDE_CODE!r} has no entry")
    return problems


def main(argv: list[str]) -> int:
    if argv != ["--check"]:
        print(__doc__.split("\n\n")[0])
        return 2
    problems = check_table()
    for p in problems:
        print(f"harness_bookkeeping: {p}")
    if not problems:
        print(f"harness_bookkeeping: ok: {len(TABLE)} harness(es): {', '.join(sorted(TABLE))}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
