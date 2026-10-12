#!/usr/bin/env python3
"""The walk register: every pre-freeze walk is listed, and every listed walk has its folder.

    python3 evals/gap-study-4/walk_register.py --check     the register against rehearsals/; exit 1 on any problem

WHY A REGISTER. The round 4 plan's CP6 (lines 870-878) makes every pre-freeze walk a rehearsal: "graded but never
counted, each committed with its reason". A folder of walk records with no list beside it cannot show that nothing
was dropped, and a list with no folders cannot show the walks happened. So rehearsals/register.json lists the walks
and this check binds the two both ways:

  - every folder directly under rehearsals/ is a registered walk (an unregistered folder fails, and so does any
    file beside register.json and README.md, which is not a walk and is never skipped);
  - every registered walk has its folder, holding at least one file (git keeps no empty folder, so an empty one is
    a folder a clone would not have);
  - every entry is well formed: exactly the fields below, a one-segment walk id used once, a task, half and wording
    the design in force has (prereg-draft.json and tasks/<task>.json), a model of the arm it names, a non-empty
    reason, and `counted` exactly false. A walk is never a data take; an entry that says otherwise is refused.

THE EMPTY GATE IS SAID OUT LOUD. No walk has been run when this file is written, so the register is empty and
--check passes, printing "ok, having registered 0 walks", never a bare ok: an empty register is not evidence about
any walk.

WHAT A WALK FOLDER HOLDS (lane w8a, ruling W8-layout-1, Option A; this file moved from lane w7d to lane w8a under
ruling W8A-gap4-1). --check also applies the content rule (content_problems): a registered walk's folder holds only
what a take folder holds (drive.py's closed map: launch, preflight, refusal, postflight, teardown, operator-check,
proxy.log, transcript.jsonl, turn-N.jsonl, driver-ledger.json, environment.json, scrub.json, evidence/**, session/**)
plus grade.json (run.regrade()'s output, or why the walk was not graded), and it holds driver-ledger.json and
grade.json. The road that writes here is drive.walk_driver(records="walks"), and drive.WalkRepo commits the folder
with its register entry in one commit. The folder's name comes from mode_binding.WALKS_DIR.
W10 (lane w10-walk-runner, rulings D1 and D3; this paragraph edited without transfer, departure w10-5): a walk folder
also holds check.json (the checker's reading and route, written by walk_runner.py), and a walk that died before its
driver ledger holds preflight.json or refusal.json in its place; the rule itself is drive.walk_files, read here.

ONE WALK, ONE COMMIT (lane w8d, ruling W8D-gap4-1, from W8A-R2-2; this file moved from lane w8a
to lane w8d). The CLI's --check also reads the repository's history (history_problems): for each registered walk,
exactly one non-merge commit in HEAD's history touches rehearsals/<walk>/, and it is a walk commit (drive.WALK_SUBJECT,
one parent, changing only that folder and the register, whose entry for the walk it adds); HEAD's tree at the folder
is the tree that commit wrote (so a merge cannot rewrite it either); and the folder on disk is HEAD's. A later
ordinary commit that edits a walk's ledger is refused. The register is append-only over history (fold W8D-close-1):
every entry a walk-subject commit's register lists is listed at HEAD, identical, so a later commit editing a walk's
reason or model, deleting a walk, or deleting and re-adding it refuses; the register on disk is HEAD's. A shallow
history refuses (the walk's commit cannot be read; CI checks out with fetch-depth 0); git is read even when no walk is
registered. WHAT THIS CANNOT SEE (W8D-R1-4): history itself can be rewritten. Amending the walk commit (or rewriting
the branch so a changed walk sits in its one walk commit), or a hand-made commit under the walk subject that adds a
walk the way WalkRepo would, both pass, since this check reads the history it is handed. Both history reads use
--full-history (W8D-R2-1), so a walk dropped by `git merge -s ours`, in either direction, is still read and refused.
drive.py's adapter class check (W8D-R1-3, W8D-R2-2) does not see in-process tampering: an object whose __class__ is
reassigned to the production class, or a fake whose __module__ is "claude_code_adapter" that drive.py captures
because drive was imported or reloaded while ClaudeCodeAdapter was patched. The backstop is outside both: CP8's
commit pins by full sha and a protected branch. The test-only --base reads the
history only when --repo names the repository; the gates (CI, freeze_rehearsal) run the bare --check, which reads
this repository's.

WHAT THIS DOES NOT CHECK (open questions in rehearsals/README.md): whether the walks cover what CP6 asks for (every
wording on the smallest model, every task and half on each model), and whether the walks are published at CP8.

No model, no network, stdlib only. Read-only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import mode_binding  # noqa: E402

REHEARSALS = HERE / mode_binding.WALKS_DIR    # W8A: the folder name is mode_binding's, never spelled here
REGISTER_NAME = "register.json"
TOP_FILES = ("README.md", REGISTER_NAME)
# Finder's folder file on the Mac; never tracked, never a walk.
IGNORED_NAMES = (".DS_Store",)
SCHEMA = 1
TOP_KEYS = ("schema", "walks")
FIELDS = ("walk", "task", "half", "wording", "arm", "model", "reason", "counted")
STRING_FIELDS = ("walk", "task", "half", "wording", "arm", "model", "reason")
WALK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class DuplicateKey(ValueError):
    pass


def no_duplicate_keys(pairs):
    """W7D-R1-3: json keeps the last of two equal keys, so `"counted": true, "counted": false` would read false."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise DuplicateKey(k)
        out[k] = v
    return out


def visible(text: str) -> str:
    """W7D-R1-6: the text without Unicode whitespace or format characters (a zero-width-only reason is empty)."""
    return "".join(c for c in text if not (c.isspace() or unicodedata.category(c) == "Cf"))


def design_in_force(study_dir: Path = HERE) -> dict:
    """What an entry is checked against: the draft's tasks and their wordings, each task's halves, each arm's
    models (the planned arms and the optional ones)."""
    draft = json.loads((study_dir / "prereg-draft.json").read_text())
    tasks = {}
    for t in draft["tasks"]:
        halves = list(json.loads((study_dir / "tasks" / f"{t['id']}.json").read_text())["halves"])
        tasks[t["id"]] = {"halves": halves, "wordings": list(t["wordings"])}
    arms = {arm: list(models) for arm, models in draft["models"].items()}
    for arm, spec in (draft.get("optional_arms") or {}).items():
        arms.setdefault(arm, []).append(spec["model"])
    return {"tasks": tasks, "arms": arms}


def entry_problems(i: int, entry, design: dict) -> list[str]:
    where = f"walk entry {i}"
    if not isinstance(entry, dict):
        return [f"{where} is not an object"]
    out = []
    if set(entry) != set(FIELDS):
        missing = sorted(set(FIELDS) - set(entry))
        extra = sorted(set(entry) - set(FIELDS))
        return [f"{where} has fields missing {missing} and unknown {extra}; an entry holds exactly {list(FIELDS)}"]
    for k in STRING_FIELDS:
        if not isinstance(entry.get(k), str) or not visible(entry[k]):
            out.append(f"{where}: {k} is not a non-empty string")
    if out:
        return out
    if entry["counted"] is not False:
        out.append(f"{where}: counted is {entry['counted']!r}; a walk is a rehearsal, graded but never counted "
                   f"(plan CP6), so counted is exactly false")
    if not WALK_ID.fullmatch(entry["walk"]):
        out.append(f"{where}: walk {entry['walk']!r} is not one path segment")
    task, design_tasks = entry["task"], design["tasks"]
    if task not in design_tasks:
        out.append(f"{where}: task {task!r} is not a task of the design in force")
    else:
        if entry["half"] not in design_tasks[task]["halves"]:
            out.append(f"{where}: half {entry['half']!r} is not a half of {task}")
        if entry["wording"] not in design_tasks[task]["wordings"]:
            out.append(f"{where}: wording {entry['wording']!r} is not a wording of {task}")
    if entry["arm"] not in design["arms"]:
        out.append(f"{where}: arm {entry['arm']!r} is not an arm of the design in force")
    elif entry["model"] not in design["arms"][entry["arm"]]:
        out.append(f"{where}: model {entry['model']!r} is not a model of arm {entry['arm']}")
    return out


def has_a_file(folder: Path) -> bool:
    """W7D-R1-2: a regular file, never a symlink (a link to a file outside the study is not a walk record)."""
    return any(p.is_file() and not p.is_symlink() and p.name not in IGNORED_NAMES for p in folder.rglob("*"))


def registered(base: Path = REHEARSALS) -> list[dict]:
    """W8A: the register's entries that name a walk id (objects with a string `walk`), in order; [] when the register
    cannot be read. For the readers (fixture_walk, build_cases, run, copy_manifest); --check is the judge of the rest."""
    try:
        hook = no_duplicate_keys
        doc = json.loads((Path(base) / REGISTER_NAME).read_text(), object_pairs_hook=hook)
    except (OSError, ValueError):
        return []
    walks = doc.get("walks") if isinstance(doc, dict) else None
    return [e for e in walks if isinstance(e, dict) and isinstance(e.get("walk"), str)] if isinstance(walks, list) else []


def content_problems(base: Path, walks) -> list[str]:
    """W8A (README Q2): each named walk's folder holds only a take folder's records plus grade.json and check.json, and
    holds grade.json, check.json and driver-ledger.json, or preflight.json or refusal.json for a walk that died before
    its first turn (W10; drive.walk_files, the same rule WalkRepo commits by). A folder that does not
    exist is check()'s to report, not this rule's."""
    import drive  # the closed map lives with the driver that writes it; imported here, never at module load
    out = []
    for walk in walks:
        folder = Path(base) / walk
        if not folder.is_dir() or folder.is_symlink():
            continue
        try:
            drive.walk_files(folder)
        except drive.DriveRefused as e:
            out.append(f"walk {walk!r}: {mode_binding.WALKS_DIR}/{walk}/ breaks the walk folder's content rule: {e}")
    return out


def check(base: Path = REHEARSALS, design: dict | None = None) -> tuple[list[str], int]:
    """(problems, number of registered walks)."""
    design = design_in_force() if design is None else design
    problems: list[str] = []
    reg = base / REGISTER_NAME
    if reg.is_symlink():
        return [f"rehearsals/{REGISTER_NAME} is a symlink; the register is a file in this folder"], 0
    if not reg.is_file():
        return [f"rehearsals/{REGISTER_NAME} is missing; an empty register is {{\"schema\": {SCHEMA}, "
                f"\"walks\": []}}, and a missing one is not empty"], 0
    try:
        text = reg.read_text()
    except OSError as exc:
        return [f"rehearsals/{REGISTER_NAME} cannot be read: {exc}"], 0
    except UnicodeDecodeError as exc:
        return [f"rehearsals/{REGISTER_NAME} is not JSON: {exc}"], 0
    try:
        doc = json.loads(text, object_pairs_hook=no_duplicate_keys)
    except DuplicateKey as exc:
        return [f"rehearsals/{REGISTER_NAME} has a duplicate key {exc.args[0]!r}; each key is written once"], 0
    except ValueError as exc:
        return [f"rehearsals/{REGISTER_NAME} is not JSON: {exc}"], 0
    if not isinstance(doc, dict) or set(doc) != set(TOP_KEYS):
        return [f"rehearsals/{REGISTER_NAME}: the top-level keys are exactly {list(TOP_KEYS)}"], 0
    if type(doc["schema"]) is not int or doc["schema"] != SCHEMA:
        problems.append(f"rehearsals/{REGISTER_NAME}: schema is {doc['schema']!r}, not {SCHEMA}")
    walks = doc["walks"]
    if not isinstance(walks, list):
        return problems + [f"rehearsals/{REGISTER_NAME}: walks is not a list"], 0
    registered: list[str] = []
    seen_fold: dict[str, str] = {}
    for i, entry in enumerate(walks):
        bad = entry_problems(i, entry, design)
        problems.extend(bad)
        if isinstance(entry, dict) and isinstance(entry.get("walk"), str):
            walk = entry["walk"]
            folded = walk.casefold()
            if walk in registered:
                problems.append(f"walk entry {i}: walk {walk!r} is registered twice")
            elif folded in seen_fold:
                # W7D-R1-1: one folder on a case-blind filesystem (the Mac), two on athena
                problems.append(f"walk entry {i}: walk {walk!r} and {seen_fold[folded]!r} differ only by case")
            seen_fold.setdefault(folded, walk)
            registered.append(walk)
    # W7D-R1-1: folders are matched by their exact listed names, never by a path lookup, which ignores case on APFS
    names = {p.name: p for p in base.iterdir()}
    for walk in dict.fromkeys(registered):
        if not WALK_ID.fullmatch(walk):
            continue
        folder = names.get(walk)
        if folder is None or folder.is_symlink() or not folder.is_dir():
            problems.append(f"walk {walk!r} is registered and rehearsals/{walk}/ does not exist as a folder")
        elif not has_a_file(folder):
            problems.append(f"walk {walk!r} is registered and rehearsals/{walk}/ holds no file")
    for p in sorted(base.iterdir()):
        name = p.name
        if name in IGNORED_NAMES:
            continue
        if p.is_dir() and not p.is_symlink():
            if name not in registered:
                problems.append(f"rehearsals/{name}/ is a walk folder the register does not list; every walk is "
                                f"registered with its reason (plan CP6)")
        elif name not in TOP_FILES:
            problems.append(f"rehearsals/{name} is a file beside the register, not a walk folder; only "
                            f"{list(TOP_FILES)} sit there")
    return problems, len(walks)


def history_problems(base: Path, walks, repo: Path) -> list[str]:
    """W8A-R2-2 (ruling W8D-gap4-1): each named walk's folder is the tree its one walk commit wrote, unchanged since;
    and (fold W8D-close-1, W8D-R1-1, W8D-R1-2) the register is append-only over history: every entry the register of a
    walk-subject commit in HEAD's history lists is listed at HEAD, identical, and the register on disk is HEAD's. git
    is read even when no walk is registered: a false "0 walks" over a deleted walk is worse than one read."""
    walks = list(walks)
    import drive  # WALK_SUBJECT lives with WalkRepo, which writes the commit; imported here, never at module load
    repo, base = Path(repo).resolve(), Path(base).resolve()
    try:
        rel_base = base.relative_to(repo).as_posix()
    except ValueError:
        return [f"{mode_binding.WALKS_DIR}/ ({base}) is not inside the repository {repo}; a walk's commit cannot be read"]

    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    got = git("rev-parse", "--is-shallow-repository")
    if got.returncode != 0:
        return [f"the repository's history cannot be read ({got.stderr.strip()[:200]}); each walk is bound to the "
                f"commit that wrote it"]
    if got.stdout.strip() != "false":
        return [f"the repository is a shallow clone: a walk's commit is not in it, so no walk can be bound to the "
                f"commit that wrote it (check out with full history, fetch-depth: 0)"]
    reg_rel = f"{rel_base}/{REGISTER_NAME}"
    out = []
    reg_dirty = git("status", "--porcelain", "--untracked-files=all", "--", reg_rel).stdout.strip()
    if reg_dirty:
        out.append(f"{mode_binding.WALKS_DIR}/{REGISTER_NAME} on disk differs from HEAD's: {reg_dirty.splitlines()[0]}")
    hook = no_duplicate_keys

    def entries_at(rev) -> dict:
        shown = git("show", f"{rev}:{reg_rel}")
        if shown.returncode != 0:
            return {}
        try:
            listed = json.loads(shown.stdout, object_pairs_hook=hook)["walks"]
        except (ValueError, KeyError, TypeError):
            return {}
        return {e["walk"]: e for e in listed if isinstance(e, dict) and isinstance(e.get("walk"), str)} \
            if isinstance(listed, list) else {}
    at_head_entries = entries_at("HEAD")
    # W8D-R2-1: --full-history, or git's default simplification prunes a merge side (merge -s ours drops a walk)
    log = git("log", "--full-history", "--no-merges", "--format=%H%x1f%s", "HEAD", "--", reg_rel)
    if log.returncode != 0:
        return out + [f"the register's history cannot be read ({log.stderr.strip()[:200]})"]
    seen: set = set()
    for line in log.stdout.splitlines():           # newest first; each walk reported once
        sha, _, subject = line.partition("\x1f")
        if not subject == drive.WALK_SUBJECT:     # only walk commits register walks
            continue
        for walk, entry in entries_at(sha).items():
            if walk in seen:
                continue
            now = at_head_entries.get(walk)
            if now is None:
                seen.add(walk)
                out.append(f"walk {walk!r} is listed by walk commit {sha[:12]} and not in HEAD's register; the "
                           f"register is append-only: a walk, once committed, is never removed")
            elif now != entry:
                seen.add(walk)
                out.append(f"walk {walk!r}: its register entry at HEAD is not the one walk commit {sha[:12]} wrote "
                           f"(fields {sorted(k for k in set(now) | set(entry) if now.get(k) != entry.get(k))}); the "
                           f"register is append-only")
    for walk in walks:
        rel = f"{rel_base}/{walk}"
        where = f"walk {walk!r}: {mode_binding.WALKS_DIR}/{walk}/"
        log = git("log", "--full-history", "--no-merges", "--format=%H%x1f%P%x1f%s", "HEAD", "--", rel + "/")
        if log.returncode != 0:
            out.append(f"{where}: its history cannot be read ({log.stderr.strip()[:200]})")
            continue
        commits = [line.split("\x1f", 2) for line in log.stdout.splitlines() if line]
        if len(commits) != 1:
            out.append(f"{where} is touched by {len(commits)} commits; a walk folder is written once, by its walk "
                       f"commit, and no later commit rewrites it")
            continue
        sha, parents, subject = commits[0]
        if subject != drive.WALK_SUBJECT:
            out.append(f"{where} was written by {sha[:12]} ({subject!r}), not by a walk commit "
                       f"({drive.WALK_SUBJECT!r}, drive.WalkRepo)")
            continue
        changed = git("diff-tree", "-r", "--name-only", "--no-renames", "--no-commit-id", sha)
        names = changed.stdout.splitlines()
        if len(parents.split()) != 1 or changed.returncode != 0 or reg_rel not in names or \
                any(n != reg_rel and not n.startswith(rel + "/") for n in names):
            out.append(f"{where}: its commit {sha[:12]} is not one walk's commit (one parent, changing only the "
                       f"walk's folder and {REGISTER_NAME})")
            continue
        try:
            hook = no_duplicate_keys        # (spelled once as a keyword argument, in check(), which R7's witness edits)
            listed = json.loads(git("show", f"{sha}:{reg_rel}").stdout, object_pairs_hook=hook)
            listed = [e.get("walk") for e in listed["walks"] if isinstance(e, dict)]
        except (ValueError, KeyError, TypeError):
            listed = []
        if walk not in listed:
            out.append(f"{where}: its commit {sha[:12]} does not register the walk in {REGISTER_NAME}")
            continue
        at_head = git("rev-parse", "--verify", "-q", f"HEAD:{rel}").stdout.strip()
        at_walk = git("rev-parse", "--verify", "-q", f"{sha}:{rel}").stdout.strip()
        if at_head != at_walk:
            out.append(f"{where} at HEAD is not the tree its walk commit {sha[:12]} wrote; a walk's records are "
                       f"never rewritten, by a commit or a merge")
            continue
        dirty = git("status", "--porcelain", "--untracked-files=all", "--", rel + "/").stdout.strip()
        if dirty:
            out.append(f"{where} on disk differs from HEAD: {dirty.splitlines()[0]}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check the walk register against rehearsals/.")
    ap.add_argument("--check", action="store_true", required=True)
    ap.add_argument("--base", help=argparse.SUPPRESS)
    ap.add_argument("--repo", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    base = Path(args.base) if args.base else REHEARSALS
    # W8A-R2-2: the history is this repository's; under the test-only --base, only the one --repo names
    repo = Path(args.repo) if args.repo else (None if args.base else mode_binding.REPO)
    try:
        problems, n = check(base)
        if not problems:                     # W8A: the content rule, on a register and folders that bind both ways
            problems = content_problems(base, [e["walk"] for e in registered(base)])
        if not problems and repo is not None:
            walks = [e["walk"] for e in registered(base)]
            problems = history_problems(base, walks, repo)   # W8A-R2-2
    except OSError as exc:
        problems, n = [f"rehearsals/ cannot be read: {exc}"], 0
    for p in problems:
        print(f"FAIL {p}")
    if problems:
        return 1
    if n == 0:
        print(f"ok, having registered 0 walks: rehearsals/ holds no walk folder and the register lists none, "
              f"so nothing here is evidence about any walk.")
    else:
        print(f"ok: {n} registered walk(s), each with its folder, none counted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
