#!/usr/bin/env python3
"""Freeze the reviewed round 4 rows, agent identities and complete owned build.

The review commit seeds a deterministic permutation of whole planned rows.
Versions come from the design; no vendor executable is run. All owned files,
including this builder, prose, checks and COPIED.d, carry committed byte pins.
The frozen file binds itself through its unique introducing commit.

Under glitch-f3's ruling w5b-3, COPIED.json is exactly derive() over the build
fragments before any output is written. COPIED.d/freeze.json claims COPIED.json,
prereg.json and itself as new. It is deliberately absent from the snapshot:
--check compares with nothing committed, so there is no circular snapshot.
The two generated non-self outputs are pinned inside prereg.json as well.
All three outputs belong to one freeze commit. Any existing output refuses a
second freeze, including an interrupted first write. Rehearsal/review evidence
must already match the committed draft and tree before the real --write.
Pass the disposable rehearsal report with --rehearsal-record; its content and
hash are retained in prereg.json, without adding that output to the build tree.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import prereg  # noqa: E402
import study  # noqa: E402
import copy_manifest  # noqa: E402
import order_beacon  # noqa: E402

DRAFT = HERE / "prereg-draft.json"
FROZEN = HERE / "prereg.json"


def output_fragment() -> dict:
    return {"lane": "freeze", "files": [
        {"path": path, "status": "new", "reason": "written once by freeze.py at the freeze"}
        for path in ("COPIED.json", "prereg.json", "COPIED.d/freeze.json")
    ]}


def outputs_exist(root: Path) -> bool:
    return any((root / p).exists() for p in ("COPIED.json", "prereg.json", "COPIED.d/freeze.json"))


def snapshot(manifest, folder: Path) -> dict:
    return manifest.derive(folder)


def write_outputs(frozen: dict, *, root=HERE, manifest=copy_manifest) -> tuple[Path, ...]:
    """Write the three outputs, for one subsequent commit; no partial write is retryable.

    The caller has checked the review, rehearsal, design and pins. This boundary
    independently checks the build's copy record before taking its snapshot.
    """
    root = Path(root)
    if outputs_exist(root):
        raise ValueError("a freeze output already exists; the freeze happens once")
    folder = root / "COPIED.d"
    bad = manifest.problems(folder)
    if bad:
        raise ValueError("cannot freeze the copy record: " + "; ".join(bad))
    copied = snapshot(manifest, folder)
    encoded = {"COPIED.json": json_bytes(copied), "COPIED.d/freeze.json": json_bytes(output_fragment())}
    frozen = copy.deepcopy(frozen)
    if "pinned_files" in frozen:
        frozen["pinned_files"].extend(generated_pins(encoded))
    encoded["prereg.json"] = json_bytes(frozen)
    for relative, data in encoded.items():
        (root / relative).write_bytes(data)
    return tuple(root / p for p in encoded)


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def generated_pins(outputs):
    return [{"path": study.rel(path), "sha256": hashlib.sha256(data).hexdigest(),
             "git_blob_sha": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}
            for path, data in sorted(outputs.items())]


def planned_order(draft, seed):
    import check_results
    rows = draft["rows"]
    check_results.validate_ledger([dict(row, attempt=1) for row in rows])
    if not rows:
        raise ValueError("the design has no planned rows")
    # Stable permutation of whole rows; the harness remains part of each cell.
    return sorted(copy.deepcopy(rows), key=lambda row: hashlib.sha256(seed.encode() + json_bytes(row)).hexdigest())


# Pre-freeze review 2, m3 (lane fold2-lb): the order function is witnessed with the draft. The draft carries the sha256
# of the source of planned_order and of every study function it reaches (take_order_function_sha256), so the push
# that witnesses the draft before the round also fixes the function that permutes its rows; the freeze refuses a draft
# whose value is not HEAD's. The walk starts at planned_order and at order_beacon.seed (the seed's derivation), and
# hashes, for every function it reaches, its source with its decorators and every module-level statement of a parsed
# module that binds a name the function reads or the function's own name (a rebinding such as `json_bytes = ...`, at
# top level or inside a module-level if, try, with or loop), and every module-level assignment to an attribute named
# like a reached function (`check_results.validate_ledger = ...`); the fold's review, m-1. What it cannot see, named
# (the review's re-check, each reproduced): a module-level patch, in any study file, of the standard library or the
# builtins the order reads (json.dumps, sorted, hashlib), by assignment or setattr; a patch of a function object
# (`planned_order.__code__ = ...`); a function reached only through a value the walk does not resolve (a dict of
# functions, getattr, a parameter); prepare's hand-off of the seed to planned_order (freeze.prepare); and anything
# outside this study's own .py files. Each is a code edit after the draft's push, visible in the diff a later review
# reads; the closing check, check_results recomputing take_order from the draft and take_order_seed at publication,
# is not built here.
ORDER_FUNCTION_HASH_KEY = "take_order_function_sha256"
ORDER_FUNCTION_START = ("freeze", "planned_order")
ORDER_FUNCTION_STARTS = (ORDER_FUNCTION_START, ("order_beacon", "seed"))


def _top_functions(tree) -> dict:
    return {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _module_bindings(tree, text) -> tuple[dict, dict]:
    """({name: [statement source]}, {attribute name: [statement source]}) over the module-level statements of `tree`
    (descending into if, try, with and loop bodies, never into a def or class body) that bind a name or assign to an
    attribute; a def binds its name too, so a second def of the same name is caught."""
    names: dict = {}
    attrs: dict = {}

    def add(table, key, node):
        table.setdefault(key, []).append(_segment(text, node))

    def visit(body):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                add(names, node.name, node)
                continue
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    continue
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    add(names, sub.id, node)
                elif isinstance(sub, ast.Attribute) and isinstance(sub.ctx, ast.Store):
                    add(attrs, sub.attr, node)
                elif isinstance(sub, ast.alias):
                    add(names, (sub.asname or sub.name).split(".")[0], node)
            for field in ("body", "orelse", "finalbody", "handlers"):
                inner = getattr(node, field, None)
                if isinstance(inner, list):
                    visit([n for n in inner if isinstance(n, ast.stmt)] +
                          [s for h in inner if isinstance(h, ast.ExceptHandler) for s in h.body])
    visit(tree.body)
    return names, attrs


def _segment(text, node) -> str:
    """A statement's source with its decorators (ast.get_source_segment starts at the def line)."""
    lines = text.splitlines(keepends=True)
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return "".join(lines[start - 1:node.end_lineno])


def _study_imports(nodes, root: Path) -> dict:
    """{local name: study module} for `import x` / `import x as y` in `nodes`, x a .py file in `root`."""
    out = {}
    for node in nodes:
        for imp in ast.walk(node):
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    if "." not in alias.name and (root / f"{alias.name}.py").is_file():
                        out[alias.asname or alias.name] = alias.name
    return out


def order_function_sources(root=None) -> list[tuple[str, str]]:
    """[(label, source)] for planned_order, order_beacon.seed and every study function they reach, found by an ast walk
    (a name or a study module's attribute that is a top-level function of that module, called or passed), each with
    its decorators; plus, labelled "module.name=", every module-level statement binding a name such a function reads
    or its own name, and every module-level attribute assignment named like a reached function (ORDER_FUNCTION_HASH_KEY's
    comment). Sorted, each once, with no line numbers, so an edit elsewhere in a file moves nothing. `root` is the
    study folder whose .py files are read: by default the folder this freeze.py runs from (not HERE, which a scratch
    study may stand in for while the modules still import from here), so the hash is of the code that runs."""
    root = Path(__file__).resolve().parent if root is None else Path(root)
    parsed: dict = {}

    def module(name):
        if name not in parsed:
            text = (root / f"{name}.py").read_text(encoding="utf-8")
            tree = ast.parse(text)
            parsed[name] = (text, tree, _top_functions(tree),
                            _study_imports([n for n in tree.body if isinstance(n, ast.Import)], root),
                            *_module_bindings(tree, text))
        return parsed[name]

    found, work, extra = {}, list(ORDER_FUNCTION_STARTS), set()
    while work:
        mod, fn = work.pop()
        if (mod, fn) in found:
            continue
        text, _, funcs, imports, names, _ = module(mod)
        node = funcs[fn]
        found[(mod, fn)] = _segment(text, node)
        aliases = dict(imports, **_study_imports([node], root))
        read = {fn} | {sub.id for sub in ast.walk(node) if isinstance(sub, ast.Name)}
        for name in read:
            for src in names.get(name, []):
                if src != found[(mod, fn)]:
                    extra.add((f"{mod}.{name}=", src))
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in funcs and sub.id != fn:
                work.append((mod, sub.id))
            elif isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id in aliases:
                target = aliases[sub.value.id]
                if sub.attr in module(target)[2]:
                    work.append((target, sub.attr))
    reached = {f for _, f in found}
    for mod, (_, _, _, _, _, attrs) in parsed.items():
        for name in reached & set(attrs):
            extra.update((f"{mod}.<attr>.{name}=", src) for src in attrs[name])
    own = set(found.values())
    return sorted({(f"{m}.{f}", src) for (m, f), src in found.items()} | {e for e in extra if e[1] not in own})


def take_order_function_sha256(root=None) -> str:
    """The sha256 over order_function_sources(root): each name, its source, in order."""
    h = hashlib.sha256()
    for name, source in order_function_sources(root):
        h.update(name.encode("utf-8") + b"\n" + source.encode("utf-8") + b"\n\0")
    return h.hexdigest()


def order_function_problem(draft):
    """Why the draft's take_order_function_sha256 is not the order function's at this tree, or None (m3)."""
    want, got = take_order_function_sha256(), draft.get(ORDER_FUNCTION_HASH_KEY)
    if got != want:
        return (f"the draft's {ORDER_FUNCTION_HASH_KEY} is {str(got)[:16]!r}, not the order function's at this tree "
                f"({want[:16]}): the function that permutes the rows is not the one the draft was witnessed with")
    return None


def draft_pending(draft) -> dict:
    """build_draft.pending over the draft itself: every PENDING input by its pointer (pre-freeze review 1, m2)."""
    import build_draft
    return build_draft.pending(draft)


def prepare(draft, *, review, parent, pins, frozen_at, beacon):
    """The frozen file from the reviewed draft. Pre-freeze review 1, m2: the stats_design sentinel was the only PENDING
    guard, so a copy with that one key replaced froze with 15 PENDING strings left; the draft's own pending() map must
    be empty. MAJOR 9: the order is seeded by order_beacon.seed over the registered drand round's reading alone
    (`beacon`, read by take_order_beacon_reading; the lane orchestrator's ruling 1 on lane L1's hand-back). The
    `review` commit is recorded as pre_freeze_review_commit and enters no seed."""
    import stats
    import completeness
    left = draft_pending(draft)
    if left:
        raise ValueError(f"the draft holds {len(left)} PENDING input(s) ({', '.join(list(left)[:6])}"
                         + (", ..." if len(left) > 6 else "") + "); a design with any PENDING input is never frozen")
    stats.validate_design(draft[stats.DESIGN_KEY])
    completeness.pair_count(draft)
    round_no = order_beacon.registered_round(draft.get(BEACON_KEY))
    bad = order_beacon.reading_problems(beacon, round_no)
    if bad:
        raise ValueError("the take-order beacon reading is refused: " + "; ".join(bad))
    seed = order_beacon.seed(beacon)
    frozen = copy.deepcopy(draft)
    frozen.update(status="FROZEN", frozen_at=frozen_at, frozen_at_commit_parent=parent,
                  pre_freeze_review_commit=review, take_order_seed=seed, take_order_beacon_reading=copy.deepcopy(beacon),
                  take_order=planned_order(draft, seed), pinned_files=copy.deepcopy(pins))
    return frozen


BEACON_KEY = "take_order_beacon"
WITNESS_NOT_REHEARSED = "not witnessed: a disposable rehearsal reads no push record"
BEACON_READING_KEY = "take_order_beacon_reading"
BEACON_NOT_REHEARSED = ("NOT REHEARSED: the take-order beacon (a disposable rehearsal given no --beacon-reading seeds "
                        "its order from a synthetic reading, marked synthetic in the frozen file)")
SYNTHETIC_SIGNATURE = hashlib.sha256(b"synthetic-rehearsal-not-a-drand-signature").hexdigest()


def synthetic_beacon_reading(round_no: int) -> dict:
    """A rehearsal's stand-in reading of the registered round, shaped like a real one and named synthetic by its
    signature (SYNTHETIC_SIGNATURE), which a real freeze refuses."""
    return {"chain_hash": order_beacon.CHAIN["chain_hash"], "round": round_no,
            "round_time": order_beacon.round_time(round_no), "signature": SYNTHETIC_SIGNATURE,
            "randomness": hashlib.sha256(bytes.fromhex(SYNTHETIC_SIGNATURE)).hexdigest(),
            "relays": list(order_beacon.RELAYS)}


REGISTERED_LINE = "REGISTERED_ROUND: int | None = {round}"


def beacon_history() -> list[tuple[str, object, tuple]]:
    """(commit, REGISTERED_ROUND, SUPERSEDED_ROUNDS) for every commit in HEAD's history that changed order_beacon.py,
    oldest first, each read by parsing that version (the review of 53d0e9af, finding 1a; option A+)."""
    rel = study.rel("order_beacon.py")
    code, out = git("log", "--reverse", "--topo-order", "--full-history", "--format=%H", "--", rel)
    if code != 0 or not out.split():
        raise ValueError(f"the history of {rel} cannot be read at HEAD")
    history = []
    for sha in out.split():
        code, text = git("show", f"{sha}:{rel}")
        if code != 0:
            raise ValueError(f"{rel} cannot be read at {sha[:12]}")
        try:
            history.append((sha, order_beacon.registered_value(text), order_beacon.superseded_value(text)))
        except order_beacon.BeaconRefused as e:
            raise ValueError(f"{rel} at {sha[:12]}: {e}") from None
    return history


def registering_commit(round_no: int) -> str:
    """The one commit in HEAD's history that set REGISTERED_ROUND to `round_no`, read by parsing order_beacon.py at
    every commit that changed it, oldest first (the review of 53d0e9af, finding 1a and 1b). ValueError unless the
    value went None, then each superseded round of HEAD's SUPERSEDED_ROUNDS in order (option A+), then `round_no`,
    and never changed again."""
    history = beacon_history()
    problem = order_beacon.history_problem([v for _, v, _ in history], round_no, history[-1][2])
    if problem:
        raise ValueError(problem)
    return next(sha for sha, v, _ in history if v == round_no)


def supersession_swaps(history) -> list[tuple[dict, str]]:
    """Option A+, steps 1-2: each SUPERSEDED_ROUNDS entry of HEAD's version with its swap commit, the first commit in
    which REGISTERED_ROUND leaves the entry's round, which must add exactly that entry; ValueError when the tuple is not
    append-only across history (each version a prefix of the next), the entry's registering_commit is not the commit
    that set its round, or another commit added the entry."""
    for (a_sha, _, a), (b_sha, _, b) in zip(history, history[1:]):
        if tuple(b[:len(a)]) != tuple(a):
            raise ValueError(f"SUPERSEDED_ROUNDS at {b_sha[:12]} does not extend its version at {a_sha[:12]}: an entry "
                             f"was removed or rewritten, and the list is append-only")
    bad = order_beacon.superseded_problems(history[-1][2]) if history else []
    if bad:
        raise ValueError("SUPERSEDED_ROUNDS at HEAD: " + "; ".join(bad))
    out = []
    for entry in history[-1][2] if history else ():
        r = entry["round"]
        regs = [sha for sha, v, _ in history if v == r]
        if not regs or entry["registering_commit"] != regs[0]:
            raise ValueError(f"the superseded entry of round {r} names registering commit "
                             f"{str(entry['registering_commit'])[:12]}, not the commit that set the round "
                             f"({regs[0][:12] if regs else 'none'})")
        at = next((i for i in range(1, len(history)) if history[i - 1][1] == r and history[i][1] != r), None)
        if at is None:
            raise ValueError(f"REGISTERED_ROUND never leaves round {r}, which SUPERSEDED_ROUNDS lists")
        before = [e.get("round") for e in history[at - 1][2]]
        if entry not in history[at][2] or r in before:
            raise ValueError(f"the swap commit {history[at][0][:12]}, which moves REGISTERED_ROUND off round {r}, "
                             f"does not add that round's entry: an entry is added by its own swap commit only")
        out.append((entry, history[at][0]))
    return out


def owner_decisions(path=None) -> list[dict]:
    """The study's committed copy of the decision rows a superseded entry cites (order_beacon.OWNER_DECISIONS, one JSON
    object per line, copied byte for byte from OrgOS's decision.jsonl); [] when the file is absent."""
    path = HERE / order_beacon.OWNER_DECISIONS if path is None else Path(path)
    if not path.is_file():
        return []
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            raise ValueError(f"{path.name} line {n} is not JSON") from None
        if not isinstance(row, dict):
            raise ValueError(f"{path.name} line {n} is not one decision row")
        rows.append(row)
    return rows


def draft_commit() -> str:
    """The last commit in HEAD's history that changed prereg-draft.json: the draft whose rows the order permutes, fixed
    by its own push before the round (finding 1c; the review's line 1 binds the review to the same bytes). Read with
    --full-history, so a merge that took a side branch's draft is not followed to that branch silently (the closure
    check of 84ab6393, finding 1): a merge that took a side branch's draft is itself the draft commit (and must be
    pushed before the round), and every commit that changed the draft must be an ancestor of the newest one in
    topological order, or two candidate draft lines exist and the freeze refuses."""
    code, out = git("log", "--full-history", "--topo-order", "--format=%H", "--", study.rel("prereg-draft.json"))
    shas = out.split() if code == 0 else []
    if not shas or not all(re.fullmatch(r"[0-9a-f]{40}", x) for x in shas):
        raise ValueError("the commits that changed prereg-draft.json cannot be read at HEAD")
    last = shas[0]
    apart = [x for x in shas[1:] if not history_contains(x, last)]
    if apart:
        raise ValueError(f"prereg-draft.json has two candidate lines in HEAD's history: {apart[0][:12]} changed it and "
                         f"is no ancestor of {last[:12]}, the newest commit that did; one draft line is frozen, never "
                         f"one chosen among")
    return last


def rev_list(*args: str) -> list[str]:
    code, out = git("rev-list", *args)
    if code != 0:
        raise ValueError(f"git rev-list {' '.join(args[:3])} ... cannot be read")
    return out.split()


def mirror_problem(pushes, registering: str):
    """Why the mirror's pushes hold a candidate this freeze did not take, or None (the closure check of 84ab6393,
    finding 1: parallel pushed branches, each with a clean history, let one be chosen after the round). Every pushed
    sha must be in this clone; and no commit those pushes hold that is not an ancestor of HEAD may set REGISTERED_ROUND
    to an integer, or change prereg-draft.json while descending from the registering commit. All the mirror's round and
    draft history sits on HEAD's one line."""
    shas = sorted({s for _, s in pushes if s and set(s) != {"0"}})
    missing = [s for s in shas if git("cat-file", "-e", f"{s}^{{commit}}")[0] != 0]
    if missing:
        return (f"{len(missing)} sha(s) the mirror records are not in this clone ({missing[0][:12]} first): fetch the "
                f"mirror's history before the freeze, which reads every pushed commit")
    if not shas:
        return None
    rel_beacon, rel_draft = study.rel("order_beacon.py"), study.rel("prereg-draft.json")
    for c in rev_list("--full-history", *shas, "--not", "HEAD", "--", rel_beacon):
        code, text = git("show", f"{c}:{rel_beacon}")
        if code != 0:
            continue
        try:
            value = order_beacon.registered_value(text)
        except order_beacon.BeaconRefused as e:
            return f"the mirror holds {c[:12]}, off HEAD's line, whose order_beacon.py cannot be read ({e})"
        if value is not None:
            return (f"the mirror holds {c[:12]}, off HEAD's line, which sets REGISTERED_ROUND to {value}: a round "
                    f"registered on another pushed branch could be the one chosen")
    for c in rev_list("--full-history", *shas, "--not", "HEAD", "--", rel_draft):
        if history_contains(registering, c):
            return (f"the mirror holds {c[:12]}, off HEAD's line, which changes prereg-draft.json after the "
                    f"registering commit {registering[:12]}: a candidate draft on another pushed branch")
    return None


WITNESS_HOST = "github.com"


def take_order_witness(draft, *, pushes=None, contains=None, decisions=None) -> dict:
    """Ruling 1 and the review of 53d0e9af (findings 1 and 2): GitHub's own push records on order_beacon.WITNESS_REPO
    must hold both the commit that registered the draft's round and the last commit that changed the draft, each
    stamped at least WITNESS_LEAD_S before the round is published; ValueError otherwise. The witness, written into the
    frozen file as take_order_witness, is each commit with the push that holds it and GitHub's stamp. `pushes` and
    `contains` stand in for push_records() and history_contains in tests.

    Option A+ (pre-freeze review 2, section 1; lane fold2-lb): each superseded round's entry is bound to its swap commit
    (supersession_swaps) and passes only by a push of that commit stamped at least order_beacon.SWAP_LEAD_S before the
    round publishes (before_publication), or by its decision row in the committed decision list (`decisions`, else
    owner_decisions(); order_beacon.decision_problem). The witness then also lists each, as `superseded`."""
    try:
        round_no = order_beacon.registered_round(draft.get(BEACON_KEY))
    except order_beacon.BeaconRefused as e:
        raise ValueError(f"the take-order beacon: {e}") from None
    pushes = push_records() if pushes is None else pushes
    contains = history_contains if contains is None else contains
    witness = {"repo": order_beacon.WITNESS_REPO, "host": WITNESS_HOST}
    registering = registering_commit(round_no)
    problem = mirror_problem(pushes, registering)
    if problem:
        raise ValueError(problem)
    for name, commit in (("registering", registering), ("draft", draft_commit())):
        problem = order_beacon.push_witness_problem(commit, round_no, pushes, contains)
        if problem:
            raise ValueError(f"the {name} commit: {problem}")
        stamp, sha = min((t, s) for t, s in pushes if contains(commit, s))
        witness.update({f"{name}_commit": commit, f"{name}_push": {"sha": sha, "stamp": stamp}})
    swaps = supersession_swaps(beacon_history())
    if swaps:
        entries = [entry for entry, _ in swaps]
        rows = owner_decisions() if decisions is None else decisions
        seen = []
        for entry, swap in swaps:
            r = entry["round"]
            if entry.get("before_publication") is True:
                problem = order_beacon.push_witness_problem(swap, r, pushes, contains, lead=order_beacon.SWAP_LEAD_S)
                if problem:
                    raise ValueError(f"the swap commit of superseded round {r} (before_publication): {problem}")
                stamp, sha = min((t, s) for t, s in pushes if contains(swap, s))
                seen.append({"round": r, "swap_commit": swap, "swap_push": {"sha": sha, "stamp": stamp}})
            else:
                problem = order_beacon.decision_problem(entry, rows, entries)
                if problem:
                    raise ValueError(f"the swap of superseded round {r}: {problem}")
                seen.append({"round": r, "swap_commit": swap, "decision": entry["decision"], "ask": entry["ask"]})
        witness["superseded"] = seen
    return witness


def push_records(repo=None) -> list[tuple[int, str]]:
    """[(unix time, pushed sha)] of every record GitHub keeps on the witness repository that puts a commit there (its
    `after` sha: pushes, force pushes, branch creations, merges; a deletion's all-zero sha is dropped), read read-only
    with `gh api` (GET /repos/{repo}/activity, every activity type: a new branch is recorded as branch_creation, not
    push). Raises ValueError when it cannot be read."""
    repo = order_beacon.WITNESS_REPO if repo is None else repo
    host = os.environ.get("GH_HOST")
    if host not in (None, "", WITNESS_HOST):
        raise ValueError(f"GH_HOST is {host!r}: the push witness is read from {WITNESS_HOST} only")
    got = subprocess.run(["gh", "api", "--hostname", WITNESS_HOST, "--paginate",
                          f"repos/{repo}/activity?per_page=100",
                          "--jq", '.[] | "\\(.timestamp)\\t\\(.after)"'], capture_output=True, text=True)
    if got.returncode != 0:
        raise ValueError(f"GitHub's push records for {repo} cannot be read with gh api: {got.stderr.strip()[:200]}")
    out = []
    for ln in got.stdout.splitlines():
        stamp, _, sha = ln.partition("\t")
        if not sha.strip() or set(sha.strip()) == {"0"}:
            continue
        try:
            out.append((int(datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()), sha.strip()))
        except ValueError:
            raise ValueError(f"an unreadable push record for {repo}: {ln[:120]!r}") from None
    return out


def history_contains(commit: str, sha: str) -> bool:
    """Whether `sha` (a pushed commit) holds `commit` in its history, read from this repository; a sha this clone does
    not have holds nothing it can show."""
    code, _ = git("merge-base", "--is-ancestor", commit, sha)
    return code == 0


def take_order_beacon_reading(draft, *, rehearsal=False, reading_file=None, opener=None, now=None):
    """MAJOR 9: the reading of the draft's registered drand round that seeds the order.

    The real freeze reads both relays itself (the network, on the Mac), after take_order_witness has held the round's
    registration and the draft to GitHub's push records. A disposable rehearsal reads a --beacon-reading file (checked
    offline: chain, round, time, randomness the sha256 of the signature) or, given none, a synthetic reading, and says
    so (BEACON_NOT_REHEARSED)."""
    try:
        round_no = order_beacon.registered_round(draft.get(BEACON_KEY))
        if rehearsal:
            if reading_file is None:
                print(BEACON_NOT_REHEARSED)
                return synthetic_beacon_reading(round_no)
            reading = json.loads(Path(reading_file).read_text(encoding="utf-8"))
            bad = order_beacon.reading_problems(reading, round_no)
            if bad:
                raise ValueError("the --beacon-reading file is refused: " + "; ".join(bad))
            return reading
        if reading_file is not None:
            raise ValueError("--beacon-reading is for a disposable rehearsal only; the real freeze reads both relays")
        reading = order_beacon.read_relays(round_no, opener=opener, now=now)
        if reading["signature"] == SYNTHETIC_SIGNATURE:
            raise ValueError("the relays answered the rehearsal's synthetic signature")
        return reading
    except order_beacon.BeaconRefused as e:
        raise ValueError(f"the take-order beacon: {e}") from None

# All files present in the ownership record are pinned, including prose,
# checks files, the builder itself and COPIED.d. Runtime records are not part of
# the build. prereg.json binds itself through its unique introducing commit.
def owned_paths(manifest=copy_manifest, folder=None) -> list[str]:
    folder = HERE / "COPIED.d" if folder is None else folder
    entries, problems = manifest.load_fragments(folder)
    if problems:
        raise ValueError("invalid ownership record: " + "; ".join(problems))
    return sorted(entry["path"] for lane, entry in entries)


def _study_files() -> list[str]:
    return [study.rel(p) for p in owned_paths()]


NOT_PINNED_AND_WHY = {study.rel("prereg.json"): "the frozen file binds itself through its introducing commit"}
# Lane pf1-l4-close (review REVIEW-pf1-l4-close-291b357 m4, the lane orchestrator's ruling of 25 Oct 2026): the approved
# price table build_draft reads its price_table and price_variants from, outside the study folder (build_draft
# PRICE_TABLE_FILE; tests/test_pf1_cost_step.py binds the two).
PINNED = [p for p in _study_files() if p not in NOT_PINNED_AND_WHY] + [
    "CLAUDE.md", "lane-reports/gap-study-4/pf1-l4-close-20261025/price-table.json"]
GLOB_CHARS = ("*", "?", "[")


def is_pattern(path: str) -> bool:
    return any(c in path for c in GLOB_CHARS)


def pattern_regex(pattern: str) -> re.Pattern:
    """An ownership pattern as a whole-path regex: `**` crosses folders, `*` and `?` stay inside one, `[` is literal
    (no fragment uses a class, so one is refused rather than read)."""
    if "[" in pattern:
        raise ValueError(f"the ownership pattern {pattern!r} uses a character class, which the freeze does not read")
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


def committed_files(prefix: str) -> list[str]:
    """Every file committed at HEAD under `prefix` (a folder), repository-relative."""
    code, out = git("ls-tree", "-r", "--name-only", "HEAD", "--", prefix)
    if code != 0:
        raise ValueError(f"the committed files under {prefix} cannot be listed at HEAD")
    return [ln for ln in out.splitlines() if ln]


def pinned_paths(paths=None) -> list[str]:
    """Pre-freeze review 1, MAJOR 2: PINNED with every ownership pattern (native-readers/**, the one today) expanded into
    the files committed at HEAD that it matches, in order, so each acceptance record and review the freeze's leg (iii)
    reads gets a pin of its own. A pattern that matches no committed file is refused: it would pin nothing."""
    paths = PINNED if paths is None else paths
    out = []
    for p in paths:
        if not is_pattern(p):
            out.append(p)
            continue
        rx = pattern_regex(p)
        literal = p[:min(p.index(c) for c in GLOB_CHARS if c in p)]
        prefix = literal.rsplit("/", 1)[0] if "/" in literal else "."
        matched = sorted(f for f in committed_files(prefix) if rx.fullmatch(f))
        if not matched:
            raise ValueError(f"the ownership pattern {p} matches no committed file, so it would pin nothing")
        out.extend(m for m in matched if m not in out)
    return out


def pin_problems(pins) -> list[str]:
    """Each pin the freeze cannot write: a missing file, one not committed at HEAD, or (the review of 53d0e9af, NIT 6)
    one whose working bytes differ from its HEAD blob, so --check never reads a dirty pinned file as ok."""
    out = []
    for p in pins:
        if p.get("missing") or p.get("uncommitted"):
            out.append(f"{p['path']}: " + ("missing" if p.get("missing") else "not committed at HEAD"))
            continue
        data = (REPO / p["path"]).read_bytes()
        if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != p.get("git_blob_sha"):
            out.append(f"{p['path']}: uncommitted edits (its bytes are not its HEAD blob)")
    return out


def git(*args: str) -> tuple[int, str]:
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


# ROUND 2, CP8. Everything the freeze WRITES, by top-level key or by the key it fills inside a task. The freeze commit's
# body carries the diff between the reviewed draft and the frozen file restricted to these keys, or the word `none`;
# a test asserts that the diff touches nothing else, so a freeze can never edit the design on the way out.
FREEZE_WRITTEN_KEYS = (
    "status", "frozen_at", "frozen_at_commit_parent", "draft_sha256_at_freeze", "pre_freeze_review_commit",
    "pre_freeze_review_file", "pre_freeze_review_sha256", "take_order_seed", "take_order", "pinned_files",
    "take_order_beacon_reading",          # pre-freeze review 1, MAJOR 9: the drand round the order is seeded by
    "take_order_witness",                 # the review of 53d0e9af, finding 2: GitHub's pushes of the round and draft
    "nulls_at_freeze", "rehearsal_record", "rehearsed_study_tree_sha256",
    "holdout_salted_digests", "holdout_wordings_per_task_version",
)
FREEZE_FILLED_INSIDE = (
    "system_under_test.gars_tree_sha_at_freeze", "harness.claude_version_at_freeze",
    "tasks[].grader", "tasks[].grader_cases", "tasks[].positive.fixture", "tasks[].control.fixture",
)
# ROUND 2, CP8, review 1 blocker 2. A record bound the draft's bytes and nothing else, and the commit it named in
# prose had been rewritten away, so any code edit between the rehearsal and the freeze passed the gate. The record
# now carries the study tree it rehearsed as data (study_tree_sha), and the freeze requires HEAD's to be the same.
REHEARSAL_TREE_PREFIX = "study tree sha256: "
# what the binding leaves out, on both sides of every comparison: the records the rehearsal and the review write
# between the rehearsal and the freeze, the frozen file itself, and the regrade record the freeze commit rewrites
# (rehearsal 9 found the record's old bytes on one side and nothing on the other)
# and (REVIEW 3, the fact for the owner) PROGRESS.md: the slice line that records a green rehearsal is
# appended AFTER it and would invalidate it every time. It is append-only prose, never read by a take, a
# check or the result, so a line added to it is not a code edit the rehearsal failed to exercise.
TREE_BINDING_EXCLUDED = (re.compile(rf"/{study.VERIFY_DIR}/freeze-rehearsal-\d+(-clean-clone)?\.txt$"),
                         re.compile(rf"/{study.REVIEW_DIR}/prefreeze-\d+(-blindness)?\.(md|txt)$"),
                         re.compile(r"/prereg\.json$"),
                         re.compile(r"/COPIED\.json$"),
                         re.compile(r"/COPIED\.d/freeze\.json$"),
                         re.compile(r"/PROGRESS\.md$"),
                         re.compile(r"/verification/round1-regrade/environment\.json$"))
RULING_LINE = "**Ruling: DO FREEZE.**"
DO_FREEZE = "DO FREEZE"
# Pre-freeze review 2, MAJOR 3 (lane fold2-lb): the one reader of a review's ruling, here and in
# review_kit/commit_review.py (which imports these three names), so the commit and the freeze can never read one report
# two ways. The pattern is the one commit_review used since round 3, anchored to a whole line.
RULING = re.compile(r"^\*\*Ruling: DO (NOT )?FREEZE\.\*\*$", re.M)
AMBIGUOUS = "ambiguous"


# glitch-45's review of fold2/lb (MJ-3): a refusing line that is not byte-canonical (a trailing space, moved emphasis,
# a heading, an NBSP or zero-width character, lower case) beside a canonical DO FREEZE line read DO FREEZE. Each line is
# also read loosely: stripped, NFKC, zero-width characters and NBSP dropped, markdown emphasis, heading and quote marks
# removed, case-folded; a line that then names a ruling of either kind is ruling-like.
_INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)
_MARKS = re.compile(r"[*_`~#>]+")
RULING_LIKE = re.compile(r"\bruling\b\W{0,20}do\W*(not\W*)?freeze\b")


def _loose(line: str) -> str:
    import unicodedata
    line = unicodedata.normalize("NFKC", line.replace("\u00a0", " ")).translate(_INVISIBLE)
    return re.sub(r"\s+", " ", _MARKS.sub(" ", line)).strip().casefold()


def read_ruling(text: str) -> str:
    """'DO FREEZE' or 'DO NOT FREEZE' only when exactly one line of `text` is a canonical ruling line (RULING) and it
    is the only ruling-like line (RULING_LIKE over each line read loosely); else AMBIGUOUS. A quoted literal inside a
    sentence that names a ruling, a loose "do not freeze" ruling line beside a DO FREEZE line, and a second ruling-like
    line of either kind all read AMBIGUOUS, which is never DO FREEZE."""
    # glitch-45's re-check of fold2/lb, R-3: a canonical ruling line inside a ``` or ~~~ fence, or behind '>', is a
    # quotation, never a ruling, and its presence makes the report ambiguous (the realistic carrier of a canonical
    # DO FREEZE literal beside a refusal worded some other way)
    lines, fence, outside = text.splitlines(), None, []
    for ln in lines:
        mark = ln.lstrip()[:3]
        if mark in ("```", "~~~") and (fence is None or fence == mark):
            fence = None if fence else mark
            continue
        quoted = re.sub(r"^\s*(>\s*)+", "", ln)
        if fence is not None or quoted != ln:
            if RULING.fullmatch(quoted.strip()):
                return AMBIGUOUS
            continue
        outside.append(ln)
    found = [m for ln in outside for m in [RULING.fullmatch(ln)] if m]
    if len(found) != 1:
        return AMBIGUOUS
    like = [ln for ln in lines if RULING_LIKE.search(_loose(ln))]
    if len(like) != 1:
        return AMBIGUOUS
    return "DO NOT FREEZE" if found[0].group(1) else DO_FREEZE
REVIEW_DIGEST_PREFIX = "prereg.json sha256: "     # line 1 of every report (review_kit/commit_review.report_problems)
REHEARSAL_LAST_LINE = "all green"


def changed_keys(draft: dict, frozen: dict) -> list[str]:
    """Every top-level key whose value differs between the draft and the frozen file, and every task-level key."""
    out = []
    for k in sorted(set(draft) | set(frozen)):
        if k == "tasks":
            continue
        a, b = draft.get(k), frozen.get(k)
        if a == b:
            continue
        # a dict the freeze fills one key inside (harness, system_under_test) is named by that key, not whole
        if isinstance(a, dict) and isinstance(b, dict):
            out.extend(f"{k}.{kk}" for kk in sorted(set(a) | set(b)) if a.get(kk) != b.get(kk))
        else:
            out.append(k)
    for i, (a, b) in enumerate(zip(draft.get("tasks", []), frozen.get("tasks", []))):
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                if k in ("positive", "control"):
                    for kk in sorted(set(a[k]) | set(b[k])):
                        if a[k].get(kk) != b[k].get(kk):
                            out.append(f"tasks[].{k}.{kk}")
                else:
                    out.append(f"tasks[].{k}")
    return sorted(set(out))


def keys_outside_the_freeze(draft: dict, frozen: dict) -> list[str]:
    """The changed keys the freeze is not allowed to write: a non-empty list means the freeze edited the design."""
    allowed = set(FREEZE_WRITTEN_KEYS) | set(FREEZE_FILLED_INSIDE)
    return [k for k in changed_keys(draft, frozen) if k not in allowed]


def commit_body_diff(draft: dict, frozen: dict) -> str:
    """What the freeze commit's body says about the bytes: the keys the freeze wrote, or `none`."""
    keys = changed_keys(draft, frozen)
    return "none" if not keys else "freeze-written keys: " + ", ".join(keys)


# ROUND 2, CP8, review 3: the pinned files outside the study (CLAUDE.md and the first study's files the carried task
# rests on) are bound with it, so an edit to any of them after the rehearsal is refused at the gate too
BOUND_OUTSIDE = tuple(p for p in PINNED if not p.startswith(study.STUDY_REL + "/"))


def study_tree_sha(rev: str = "HEAD", also_excluded: tuple[str, ...] = ()) -> str:
    """The study's tree at a revision, plus every pinned file outside it, as `git ls-tree -r` prints them with the
    excluded records dropped, hashed.

    `also_excluded` names paths to drop as well, for a caller with a reason; the frozen file and the regrade record are
    already in TREE_BINDING_EXCLUDED, so check_results.py's comparison of the freeze commit with the rehearsal needs none.
    """
    code, out = git("ls-tree", "-r", rev, "--", study.STUDY_REL, *BOUND_OUTSIDE)
    if code != 0 or not out.strip():
        raise SystemExit(f"REFUSING: the study tree at {rev} cannot be listed ({out.strip()[:200]}). Nothing was written.")
    kept = [ln for ln in out.splitlines()
            if not any(p.search(ln) for p in TREE_BINDING_EXCLUDED) and ln.split("\t", 1)[-1] not in also_excluded]
    return hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()


# W8B (lane w8b-holdout-digests), ruling W8B-gap4-1, Javier's own decision ("holdout digests A", Mon 12 Oct 2026
# 08:51 EDT): the holdout's salted digests and its per-version count enter this repository only here, in the freeze
# commit's frozen file, read from a digest-only source that lives in private aegis (--holdout-digests). The freeze
# refuses by name when that source is not given or is not a file, rather than write empty values; only a disposable
# rehearsal may go without it, and then writes neither field and says so. The draft never carries them
# (build_draft.prefreeze_holdout_problems, applied again here and by --check).
HOLDOUT_KEYS = ("holdout_salted_digests", "holdout_wordings_per_task_version")
HOLDOUT_SOURCE_KEY = "salted_sha256"
HOLDOUT_ABSENT = ("the holdout digest source is absent: the salted digests and their count live only in private aegis "
                  "until the freeze commit (ruling W8B-gap4-1); give --holdout-digests <file>. Nothing was written.")
HOLDOUT_NOT_REHEARSED = ("NOT REHEARSED: the holdout digests (a disposable rehearsal given no --holdout-digests writes "
                         "neither field)")


def holdout_source_problem(source, rehearsal: bool):
    """Why the freeze cannot read its holdout source, or None. Only a disposable rehearsal may go without one."""
    if source is None:
        return None if rehearsal else HOLDOUT_ABSENT
    if not Path(source).is_file():
        return HOLDOUT_ABSENT
    return None


def _unique_pairs(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("the holdout digest source repeats a key")
    return dict(pairs)


# W8B-R1-1 (ruling W8B-close-1): the rehearsal's synthetic digests are made here, so the real freeze knows them: the
# sha256 of SYNTHETIC_PREFIX + task + "-" + index, index below SYNTHETIC_BOUND. A freeze that is not a disposable
# rehearsal refuses a source holding any of them, for any task of that source.
SYNTHETIC_PREFIX = "synthetic-rehearsal-not-a-wording-"
SYNTHETIC_BOUND = 8
SYNTHETIC_PER_TASK = 2


def synthetic_digest(task: str, index: int) -> str:
    return hashlib.sha256(f"{SYNTHETIC_PREFIX}{task}-{index}".encode()).hexdigest()


def synthetic_holdout_source(draft_file, out_file, per_task: int = SYNTHETIC_PER_TASK) -> dict:
    """A digest-only source for a rehearsal's freeze: synthetic hex digests, one list per task of the draft."""
    if not 0 < per_task <= SYNTHETIC_BOUND:
        raise ValueError(f"a synthetic source holds 1 to {SYNTHETIC_BOUND} digests per task")
    tasks = [task["id"] for task in json.loads(Path(draft_file).read_text())["tasks"]]
    source = {HOLDOUT_SOURCE_KEY: {task: [synthetic_digest(task, i) for i in range(per_task)] for task in tasks}}
    Path(out_file).write_text(json.dumps(source, indent=2) + "\n")
    return source


def synthetic_tasks(digests: dict) -> list[str]:
    """The tasks of a digest map whose list holds a synthetic digest of any of its tasks."""
    known = {synthetic_digest(task, i) for task in digests for i in range(SYNTHETIC_BOUND)}
    return sorted(task for task, values in digests.items() if isinstance(values, list) and known & set(values))


def holdout_fields(source, task_ids, *, rehearsal: bool = False) -> dict:
    """The two freeze-written holdout fields, from a source holding exactly {"salted_sha256": {task: [digest, ...]}}:
    no salt, wording or other key. The count is the source's, the same for every task version. Outside a disposable
    rehearsal, a source holding the rehearsal's synthetic digests is refused (W8B-R1-1)."""
    data = json.loads(Path(source).read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
    if not isinstance(data, dict) or set(data) != {HOLDOUT_SOURCE_KEY}:
        raise ValueError(f"the holdout digest source holds exactly {HOLDOUT_SOURCE_KEY}: no salt, wording or other key")
    import build_draft
    count = build_draft.validate_digests(data[HOLDOUT_SOURCE_KEY], list(task_ids))
    synthetic = synthetic_tasks(data[HOLDOUT_SOURCE_KEY])
    if not rehearsal and synthetic:
        raise ValueError("the holdout digest source holds the rehearsal's synthetic digests (" + ", ".join(synthetic)
                         + "); a real freeze takes only the salted digests from private aegis (ruling W8B-gap4-1)")
    return {"holdout_salted_digests": data[HOLDOUT_SOURCE_KEY], "holdout_wordings_per_task_version": count}


# Lane vendor-admission T3 (glitch-b5, 16 Oct 2026), ruling Q-3 (glitch-2f, 12 Oct 2026; codex_adapter.py:9-14,
# gemini_adapter.py:9-14): arms O and G are built on DOCUMENTED stream shapes, and the freeze refuses any arm whose
# adapter has not been re-tested on a stream recorded at its first real walk. Each vendor harness's adapter module
# says which it is (SHAPES_SOURCE); it is imported only when the draft has a row of that harness.
SHAPES_ADAPTERS = {"codex": "codex_adapter", "gemini": "gemini_adapter"}
RECORDED_SHAPES = "recorded"


def unrecorded_shapes_problem(draft):
    """Why the freeze refuses the draft's vendor arms (each arm and leg named), or None. Lane vendor-admission T4 PF
    (lane-reports/vendor-T4-PLAN.md v4 section 7, ruled by glitch-b5 on 17 Oct 2026): a row whose harness is codex or
    gemini is frozen only when all three legs hold for that harness: (i) its adapter's SHAPES_SOURCE is "recorded"
    (T3); (ii) check_take.VENDOR_CHECK_SHAPES_SOURCE is "recorded" and every VENDOR_PENDING_ROWS row of the harness is
    settled; (iii) native_reader_registration.production_readers() holds the harness."""
    import importlib
    rows = draft.get("rows") or []
    bad = []
    for harness in sorted({(r.get("agent") or {}).get("harness") for r in rows} & set(SHAPES_ADAPTERS)):
        module = SHAPES_ADAPTERS[harness]
        legs = []
        adapter = importlib.import_module(module)
        source = adapter.SHAPES_SOURCE
        if source != RECORDED_SHAPES:
            legs.append(f"leg i: {module}.py's SHAPES_SOURCE is {source!r}")
        else:
            legs += [f"leg i: {p}" for p in shapes_binding_problems(harness, adapter, draft)]
        legs += [f"leg ii: {p}" for p in vendor_reader_problems(harness)]
        legs += [f"leg ii: {p}" for p in fixture_binding_problems(harness, draft)]
        legs += [f"leg iii: {p}" for p in registration_problems(harness)]
        arms = sorted({r.get("arm") for r in rows if (r.get("agent") or {}).get("harness") == harness}, key=str)
        bad += [f"arm {arm} ({harness}): {leg}" for arm in arms for leg in legs]
    if not bad:
        return None
    return ("the freeze refuses " + "; ".join(bad) + f"; each leg must read {RECORDED_SHAPES!r} or hold: an arm whose "
            "adapter and checker readers were never re-tested on a stream recorded at its first real walk, or whose "
            "native reader is not registered, is never frozen (ruling Q-3; T4 plan section 7)")


def vendor_reader_problems(harness):
    """Leg (ii): check_take's vendor readers were re-tested on a recorded walk (every READER item on a RECORDED
    fixture; round 8 ruling 3, lane vendor-admission T4 P2) and every PENDING row is settled."""
    import check_take
    if harness not in check_take.VENDOR_PENDING_ROWS:
        return [f"check_take.py's VENDOR_PENDING_ROWS has no {harness} block"]
    source = check_take.VENDOR_CHECK_SHAPES_SOURCE.get(harness)
    out = [] if source == RECORDED_SHAPES else [f"check_take.py's VENDOR_CHECK_SHAPES_SOURCE is {source!r}"]
    out += check_take.vendor_reader_items_problems(harness)
    return out + check_take.vendor_rows_problems(harness)


def pinned_cli(harness, draft):
    """The harness's CLI as its RECORDED fixtures must name it: "<cli> <version>", the version the draft's rows of the
    harness all carry (pre-freeze review 1, m3); None when the rows carry other than exactly one version."""
    import check_take
    versions = {(r.get("agent") or {}).get("version") for r in draft.get("rows") or []
                if (r.get("agent") or {}).get("harness") == harness}
    if len(versions) != 1 or not isinstance(next(iter(versions)), str):
        return None
    return f"{check_take.VENDOR_FIXTURE_CLI[harness]} {versions.pop()}"


def shapes_binding_problems(harness, adapter, draft):
    """Leg (i), pre-freeze review 1 m3: an adapter's SHAPES_SOURCE "recorded" holds only with its SHAPES_RECORDED_ON
    fixture a byte copy of a committed walk record on the pinned CLI (check_take.recorded_binding_problem)."""
    import check_take
    cli = pinned_cli(harness, draft)
    if cli is None:
        return [f"the draft's {harness} rows do not carry exactly one agent version"]
    fixture = getattr(adapter, "SHAPES_RECORDED_ON", None)
    problem = check_take.recorded_binding_problem(harness, fixture, cli)
    return [f"{adapter.__name__}.py's SHAPES_RECORDED_ON: {problem}"] if problem else []


def fixture_binding_problems(harness, draft):
    """Leg (ii), pre-freeze review 1 m3: both tables hold their registered items, and every RECORDED fixture their
    rows and items name is a byte copy of a committed walk record on the pinned CLI."""
    import check_take
    out = check_take.vendor_minimum_problems(harness)
    cli = pinned_cli(harness, draft)
    if cli is None:
        return out + [f"the draft's {harness} rows do not carry exactly one agent version"]
    for fixture in check_take.vendor_fixtures_named(harness):
        problem = check_take.recorded_binding_problem(harness, fixture, cli)
        if problem:
            out.append(problem)
    return out


def registration_problems(harness):
    """Leg (iii): Javier's committed acceptance registers the harness's native reader; a refusing registry is named,
    never a traceback, and so is one that cannot run (no git binary, or any other OSError; round 8 ruling 1)."""
    import native_reader_registration
    try:
        readers = native_reader_registration.production_readers()
    except native_reader_registration.RegistrationRefused as e:
        return [f"the native-reader registry refuses: {e}"]
    except OSError as e:
        return [f"the native-reader registry could not run ({type(e).__name__}: {e})"]
    return [] if harness in readers else [f"no native reader is registered for {harness} (no committed acceptance)"]


def coverage_problem(draft=None):
    """Pre-freeze review 1, MAJOR 4 part 3: why the walks the freeze rests on do not cover the design, or None.

    walk_plan's --coverage reading, in process (walk_plan.coverage_report): every required walk of an arm the freeze
    runs must be covered by a graded walk; a deferred arm's coverage is printed as recorded, not required (OD105:
    arm G runs exactly as registered, only after a later go, whose precondition is its complete coverage)."""
    import walk_plan
    try:
        rep = walk_plan.coverage_report()
    except (walk_plan.PlanRefused, walk_plan.RegisterUnreadable, OSError, ValueError, KeyError) as e:
        return f"the walk coverage cannot be read: {e}"
    for line in walk_plan.deferred_lines(rep["got"], rep["specs"], rep["deferred"]):
        print("freeze: " + line)
    gaps = walk_plan.run_arm_gaps(rep["got"], rep["deferred"])
    if not gaps:
        return None
    per: dict = {}
    for s in gaps:
        per[(s["arm"], s["model"])] = per.get((s["arm"], s["model"]), 0) + 1
    named = "; ".join(f"arm {a}, {m}: {n} missing" for (a, m), n in per.items())
    return (f"{len(gaps)} required walk(s) of the arms the freeze runs are not covered by a graded walk ({named}); "
            f"walk_plan.py --coverage --require-run-arms names each")


def draft_holdout_problem(draft):
    """A pre-freeze draft carrying a freeze-only holdout field is refused, here as in the writer."""
    import build_draft
    bad = build_draft.prefreeze_holdout_problems(draft)
    return ("the draft carries " + ", ".join(bad) + " before the freeze; they enter at the freeze commit only "
            "(ruling W8B-gap4-1)") if bad else None


REHEARSAL_STEP = re.compile(r"\[(-?\d+)\] (.+)")
REHEARSAL_ROW_FILE = "<scratch>/row.json"      # freeze_rehearsal.main's row file, as its report masks the scratch path


def rehearsal_required_steps() -> list[str]:
    """Pre-freeze review 2, m2 (lane fold2-lb): every step a green rehearsal record must name, in freeze_rehearsal.main's
    order: the freeze, the holdout digests, the take-order beacon, the live-box step, each COMMANDS step (the holdout
    gate as the --holdout-tool run, HOLDOUT_STEP_LABEL, never the OWED line), and each runtime step."""
    import freeze_rehearsal as fr
    names = ["freeze", "holdout digests", "take-order beacon", fr.LIVE_BOX_STEP]
    names += [fr.HOLDOUT_STEP_LABEL if c == fr.HOLDOUT_GATE else " ".join(c) for c in fr.COMMANDS]
    return names + [" ".join(c) for c in fr.runtime_commands(REHEARSAL_ROW_FILE)]


def rehearsal_step_problems(lines: list[str]) -> list[str]:
    """Pre-freeze review 2, m2 (lane fold2-lb): why a rehearsal record's steps are not every required step, each named
    once with code 0, the live-box step's tail its closed pass line (freeze_rehearsal.LIVE_BOX_OK), and no step with
    another code; [] when they are. A hand-written record with only the digest, tree and last lines is refused. The
    live-box step may become a cited residual only by a ruling not yet made (FREEZE-PATH step 5): no such road exists
    here, so the step must pass."""
    import freeze_rehearsal as fr
    steps = [(i, m.group(1), m.group(2)) for i, ln in enumerate(lines) for m in [REHEARSAL_STEP.fullmatch(ln)] if m]
    out = [f"step {name!r} exited {code}" for _, code, name in steps if code != "0"]
    for name in rehearsal_required_steps():
        at = [i for i, code, n in steps if n == name and code == "0"]
        if len(at) != 1:
            out.append(f"step {name!r} is named {len(at)} times with code 0, not once")
        elif name == fr.LIVE_BOX_STEP:
            tail = lines[at[0] + 1].strip() if at[0] + 1 < len(lines) else ""
            if not fr.LIVE_BOX_OK.fullmatch(tail):
                out.append(f"step {name!r} does not end on the live-box verifier's closed pass line")
    return out


def rehearsal_evidence(record, digest: str, tree: str) -> dict:
    """Bind an external rehearsal output without changing the rehearsed tree. Pre-freeze review 2, m2: every step by
    name (rehearsal_step_problems), not the first, tree and last lines alone."""
    if record is None:
        raise ValueError("a green rehearsal record is required (--rehearsal-record)")
    record = Path(record)
    data = record.read_bytes()
    text = data.decode("utf-8")
    lines = text.rstrip().splitlines()
    if (not lines or lines[0] != digest or lines[-1] != REHEARSAL_LAST_LINE or
            [line for line in lines if line.startswith(REHEARSAL_TREE_PREFIX)] !=
            [REHEARSAL_TREE_PREFIX + tree]):
        raise ValueError("the rehearsal must be green for this draft and committed tree")
    steps = rehearsal_step_problems(lines)
    if steps:
        raise ValueError("the rehearsal record does not name every step green: " + "; ".join(steps[:6]))
    return {"name": record.name, "sha256": hashlib.sha256(data).hexdigest(), "text": text}


def pin(path: str) -> dict:
    f = REPO / path
    if not f.is_file():
        return {"path": path, "missing": True}
    code, blob = git("rev-parse", f"HEAD:{path}")
    return {
        "path": path,
        "git_blob_sha": blob if code == 0 else None,
        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
        "uncommitted": code != 0,
    }


def review_file_problems(review_commit: str) -> tuple[list[str], str | None]:
    """The seed commit must land exactly one review report, committed exactly once (review 14, F5).

    The take order is seeded by the review commit's sha. A report re-committed under another message or
    time yields another sha and another order, so the operator could choose among as many orders as it
    cared to commit. One report, one commit, recorded in the frozen file, lets a reader see it was not.
    """
    code, touched = git("show", "--name-only", "--format=", review_commit)
    if code != 0:
        return [f"{review_commit[:12]} cannot be read"], None
    reports = [ln for ln in touched.splitlines()
               if re.search(rf"^{re.escape(study.rel(study.REVIEW_DIR))}/prefreeze-\d+\.md$", ln)]
    if len(reports) != 1:
        return [f"{review_commit[:12]} lands {len(reports)} pre-freeze review reports; the seed must land exactly one"], None
    code, hist = git("log", "--format=%H", "--", reports[0])
    if len(hist.split()) != 1:
        return [f"{reports[0]} was committed {len(hist.split())} times; the seed would be one of several candidates"], None
    # ROUND 2, CP8, review 1 follow-up: the seed's report must have ruled for the freeze, and must be the latest
    # review committed, so a freeze cannot seed from an earlier or a refusing review
    # Pre-freeze review 2, MAJOR 3 (lane fold2-lb): the ruling is read from exactly one anchored ruling line, never as
    # a substring, so a DO NOT FREEZE report that quotes the other ruling in a sentence no longer seeds a freeze
    code, body = git("show", f"{review_commit}:{reports[0]}")
    ruling = read_ruling(body)
    if ruling != DO_FREEZE:
        return [f"{reports[0]} at {review_commit[:12]} ruled {ruling} (exactly one ruling line is read, by "
                f"freeze.read_ruling, which review_kit/commit_review.py records too): the freeze runs only on a review that ruled "
                f"{DO_FREEZE}"], None
    # Pre-freeze review 1, MAJOR 3: the seed review must have read the bytes being frozen. Its line 1 names the sha256
    # of the prereg.json the reviewer was handed (review_kit/commit_review.py binds it to the kit's copy); a DO FREEZE
    # review of earlier bytes never seeds a freeze of later ones, so a criterion edited after review is not frozen.
    want = REVIEW_DIGEST_PREFIX + hashlib.sha256(DRAFT.read_bytes()).hexdigest()
    first = body.split("\n", 1)[0]
    if first != want:
        return [f"{reports[0]} at {review_commit[:12]} reviewed other bytes: its line 1 is {first[:90]!r}, and the draft "
                f"being frozen needs {want!r}; a review of other bytes cannot seed this freeze"], None
    code, names = git("ls-tree", "-r", "--name-only", "HEAD", "--", study.rel(study.REVIEW_DIR))
    numbers = [int(m.group(1)) for ln in names.splitlines() for m in [re.search(r"prefreeze-(\d+)\.md$", ln)] if m]
    n = int(re.search(r"prefreeze-(\d+)\.md$", reports[0]).group(1))
    if numbers and n != max(numbers):
        return [f"{reports[0]} is not the latest review committed (prefreeze-{max(numbers)}.md is): the freeze seeds "
                f"from the last ruling, not a chosen one"], None
    problem = (registered_review_problem(reports[0], n)        # pre-freeze review 3, m2 (lane fold3/m1)
               or later_review_problem(reports[0], n)          # pre-freeze review 6, M1 (lane fold8/review-binding)
               or grandfathered_seed_problem(reports[0], n)    # pre-freeze review 6, M1
               or launch_binding_problem(reports[0], n))       # pre-freeze review 6, M2
    if problem:
        return [problem], None
    return [], reports[0]


def _register_rel() -> str:
    return f"{study.rel(study.REVIEW_DIR)}/rounds.json"


def _rows(text: str):
    """A register blob's rows, or None when the blob is not the register's shape."""
    try:
        rows = json.loads(text)["rows"]
    except (ValueError, KeyError, TypeError):
        return None
    return rows if isinstance(rows, list) else None


def _report_of(row: dict) -> str | None:
    """The committed report path a register row names (review_kit/rounds.py REPORT), or None for an unknown kind."""
    folder = {"prefreeze": (study.REVIEW_DIR, "prefreeze"), "verify": (study.VERIFY_DIR, "verify")}.get(row.get("kind"))
    if folder is None or type(row.get("n")) is not int:
        return None
    return f"{study.rel(folder[0])}/{folder[1]}-{row['n']}.md"


def ever_committed(path: str) -> bool:
    """Whether any commit reachable from any ref (git log --all) touched `path`: added, changed or deleted it."""
    code, out = git("log", "--all", "--format=%H", "-1", "--", path)
    return code != 0 or bool(out)          # an unreadable history reads as committed: fail closed


def later_review_problem(report: str, n: int) -> str | None:
    """Pre-freeze review 6, M1 (lane fold8/review-binding; glitch-45's ruling of Mon 2 Nov 2026): why a review later
    than round n exists, or a registered round was closed over a committed report, or None. review_file_problems read
    "the latest review" from the reports in HEAD's tree, so one commit deleting a later round's report and blindness
    record and marking its row spent_without_work made an earlier approving round the seed. Now the latest is read from
    three places, none of which that commit can rewrite: (a) the highest prefreeze n in review_kit/rounds.json, at HEAD
    and in every committed version of it on any ref, spent, voided and open rows included; (b) every prefreeze-M.md ever
    committed on any ref (git log --all over the review folder); and (c) at HEAD, any row marked spent_without_work or
    voided_by whose report was ever committed refuses the seed, since a round that produced a report was never spent and
    a void records no report (review_kit/rounds.py)."""
    reg = _register_rel()
    code, shas = git("log", "--all", "--format=%H", "--", reg)
    if code != 0:
        return f"the history of {reg} cannot be read, so the latest registered round is unknown: no seed"
    numbers, head_rows = set(), None
    for rev in ["HEAD", *shas.split()]:
        c, blob = git("show", f"{rev}:{reg}")
        if c != 0:
            continue                              # a commit that deleted the register holds no version of it
        rows = _rows(blob)
        if rows is None:
            return f"{reg} at {rev[:12]} is not the register's shape, so the rounds it registered are unknown: no seed"
        if rev == "HEAD":
            head_rows = rows
        numbers |= {r["n"] for r in rows if isinstance(r, dict) and r.get("kind") == "prefreeze"
                    and type(r.get("n")) is int}
    if numbers and max(numbers) > n:
        return (f"round {max(numbers)} is registered in {reg} (at HEAD or in its history, spent, voided and open rows "
                f"included), so {report} (round {n}) is not the latest review: the freeze seeds from the last ruling")
    folder = study.rel(study.REVIEW_DIR)
    code, names = git("log", "--all", "--format=", "--name-only", "--", folder)
    if code != 0:
        return f"the history of {folder} cannot be read, so the latest committed review is unknown: no seed"
    ever = {int(m.group(1)) for ln in names.splitlines()
            for m in [re.fullmatch(rf"{re.escape(folder)}/prefreeze-(\d+)\.md", ln.strip())] if m}
    if ever and max(ever) > n:
        return (f"{folder}/prefreeze-{max(ever)}.md was committed (git log --all), so {report} (round {n}) is not the "
                f"latest review, whether or not that report is in HEAD's tree: the freeze seeds from the last ruling")
    for i, row in enumerate(head_rows or []):
        if not isinstance(row, dict) or not (row.get("spent_without_work") or row.get("voided_by")):
            continue
        rep = _report_of(row)
        if rep is None or ever_committed(rep):
            return (f"row {i} of {reg} is marked spent without work or voided, and its report {rep} was committed "
                    f"(git log --all): a round that produced a report is never closed so, and no seed is read past it")
    return None


def grandfathered_seed_problem(report: str, n: int) -> str | None:
    """Pre-freeze review 6, M1: rounds 1-4 (REPORT_DIGEST_GRANDFATHERED) predate the report digest, so no record binds
    their committed bytes to what their reviewers wrote (review 4's were masked before commit). None of them seeds a
    freeze, whatever the register or the tree says; registered_review_problem still reads them as registered rounds."""
    if n in REPORT_DIGEST_GRANDFATHERED:
        return (f"{report} is round {n}, grandfathered from the report digest (REPORT_DIGEST_GRANDFATHERED): nothing "
                f"binds its committed bytes to its reviewer's session, so it never seeds the freeze")
    return None


# Pre-freeze review 6, M2 (lane fold8/review-binding): the two records whose only change a seed round may bring, beyond
# its report, its blindness record and the register, is entries appended for exactly that report and record. The copy
# record must claim them (copy_manifest --check, the freeze's first step), and a reviewer's report is excused, never
# edited, when the language lint reads it (as rounds 1-6 were). Nothing else in either file may change.
REVIEW_CLAIMS_FRAGMENT = "COPIED.d/review-records.json"
LANGUAGE_ALLOWLIST = "language-allowlist.json"


def _appended(old: list, new: list) -> list | None:
    """The entries `new` appends to `old` (old a prefix of new, order kept), or None when `new` changes anything else."""
    if not isinstance(old, list) or not isinstance(new, list) or new[:len(old)] != old:
        return None
    return new[len(old):]


def _record_only_change(path: str, launch: str, own: tuple[str, str]) -> bool:
    """Whether `path`'s change from `launch` to HEAD is entries appended for exactly the seed round's own report and
    blindness record (`own`, repository-relative), in REVIEW_CLAIMS_FRAGMENT or LANGUAGE_ALLOWLIST and nowhere else."""
    c1, before = git("show", f"{launch}:{path}")
    c2, after = git("show", f"HEAD:{path}")
    if c1 or c2:
        return False                              # added or deleted since the launch: never record-only
    try:
        before, after = json.loads(before), json.loads(after)
    except ValueError:
        return False
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if path == study.rel(REVIEW_CLAIMS_FRAGMENT):
        key, mine = "files", {p[len(study.STUDY_REL) + 1:] for p in own}
        fits = (lambda e: isinstance(e, dict) and set(e) <= {"path", "status", "reason"} and e.get("path") in mine
                and e.get("status") == "new")
    elif path == study.rel(LANGUAGE_ALLOWLIST):
        key, mine = "excused", set(own)
        fits = lambda e: isinstance(e, dict) and e.get("file") in mine   # noqa: E731
    else:
        return False
    if {k: v for k, v in before.items() if k != key} != {k: v for k, v in after.items() if k != key}:
        return False
    added = _appended(before.get(key), after.get(key))
    return bool(added) and all(fits(e) for e in added) and (
        key != "files" or len({e["path"] for e in added}) == len(added))


def launch_binding_problem(report: str, n: int) -> str | None:
    """Pre-freeze review 6, M2 (lane fold8/review-binding; glitch-45's ruling of Mon 2 Nov 2026): why the code being
    frozen is not the code round n's reviewer was handed, or None. The seed was bound to the frozen draft through its
    report's line 1 alone, so take-path and freeze code could change after a verdict with the draft byte-unchanged.
    Now every path in PINNED (each ownership pattern read as its whole folder, and the whole COPIED.d folder, so a file
    added or removed under either is read too) must have at HEAD the bytes it had at the round's launch_commit in
    review_kit/rounds.json, the commit the reviewer was handed. Only the round's own report, its blindness record and
    rounds.json may differ, by name, pinned or not; and REVIEW_CLAIMS_FRAGMENT and LANGUAGE_ALLOWLIST only by entries
    appended for exactly that report and record (_record_only_change). The first differing path is named. A code change
    after a review therefore needs a new round."""
    reg = _register_rel()
    code, text = git("show", f"HEAD:{reg}")
    rows = _rows(text) if code == 0 else None
    found = [r for r in rows or [] if isinstance(r, dict) and r.get("kind") == "prefreeze" and r.get("n") == n]
    if len(found) != 1:
        return f"{reg} holds {len(found)} prefreeze row(s) numbered {n} at HEAD, so {report} has no launch_commit"
    launch = found[0].get("launch_commit")
    if not (isinstance(launch, str) and re.fullmatch(r"[0-9a-f]{40}", launch)):
        return f"round {n}'s row in {reg} names no launch_commit, so nothing says what code its reviewer read: no seed"
    code, got = git("rev-parse", "--verify", "-q", f"{launch}^{{commit}}")
    if code != 0 or got != launch:
        return f"round {n}'s launch_commit {launch[:12]} is not a commit in this repository: no seed"
    if subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", launch, "HEAD"],
                      capture_output=True).returncode != 0:
        return f"round {n}'s launch_commit {launch[:12]} is not an ancestor of HEAD: the code its reviewer read is not this line's"
    try:
        paths = pinned_paths(PINNED)
    except ValueError as e:
        return f"the pinned paths cannot be listed ({e}), so the code being frozen cannot be compared: no seed"
    folders = [p[:min(p.index(c) for c in GLOB_CHARS if c in p)].rsplit("/", 1)[0] for p in PINNED if is_pattern(p)]
    spec = sorted(set(paths) | set(folders) | {study.rel("COPIED.d")})
    out = subprocess.run(["git", "-C", str(REPO), "diff", "--no-renames", "--no-ext-diff", "--name-only", "-z",
                          launch, "HEAD", "--", *spec], capture_output=True)
    if out.returncode != 0:
        return f"git diff {launch[:12]} HEAD over the pinned paths failed, so the code being frozen is unread: no seed"
    blind = report[:-len(".md")] + "-blindness.txt"
    allowed = {report, blind, reg}
    differ = [p for p in out.stdout.decode("utf-8", "surrogateescape").split("\0") if p and p not in allowed
              and not _record_only_change(p, launch, (report, blind))]
    if differ:
        return (f"{differ[0]} at HEAD is not its bytes at round {n}'s launch_commit {launch[:12]} ({len(differ)} pinned "
                f"path(s) differ): the code being frozen is not the code {report}'s reviewer read, so a new round is "
                f"needed")
    return None


def registered_review_problem(report: str, n: int) -> str | None:
    """Pre-freeze review 3, m2 (lane fold3/m1; glitch-45's ruling 3, Fri 30 Oct 2026): why the seed review is not a
    registered round, or None. review_file_problems never read review_kit/rounds.json, and rounds.py --check grades the
    registered rows only, so a committed prefreeze-N.md with no row N could seed the freeze. Now, at HEAD: the register
    holds exactly one prefreeze row numbered N, neither voided nor spent; that row was introduced by a commit of the
    register (the first commit whose register holds it, rounds.row_commits' reading); and the report's committed
    blindness record names the session id that commit derives (takes.session_id_for, rounds.check's binding). So a
    review run with no row registered before it opened never seeds a freeze."""
    reg = f"{study.rel(study.REVIEW_DIR)}/rounds.json"
    code, text = git("show", f"HEAD:{reg}")
    try:
        rows = json.loads(text)["rows"] if code == 0 else None
    except (ValueError, KeyError, TypeError):
        rows = None
    if not isinstance(rows, list):
        return f"{reg} cannot be read at HEAD, so {report} is no registered round: the freeze seeds only from one"
    idx = [i for i, r in enumerate(rows) if isinstance(r, dict) and r.get("kind") == "prefreeze" and r.get("n") == n]
    if len(idx) != 1:
        return (f"{report} has {len(idx)} prefreeze row(s) numbered {n} in {reg}, not exactly one: a review with no "
                f"registered round never seeds the freeze")
    i = idx[0]
    if rows[i].get("voided_by") or rows[i].get("spent_without_work"):
        return f"{report}'s round (row {i} of {reg}) is voided or spent without work, so it seeds no freeze"
    code, shas = git("log", "--reverse", "--format=%H", "--", reg)
    row_commit = None
    for sha in shas.split() if code == 0 else []:
        c, blob = git("show", f"{sha}:{reg}")
        try:
            if c == 0 and len(json.loads(blob)["rows"]) > i:
                row_commit = sha
                break
        except (ValueError, KeyError, TypeError):
            continue
    if row_commit is None:
        return f"row {i} of {reg} was introduced by no commit, so no session id can be derived for {report}"
    import takes
    want = takes.session_id_for(row_commit)
    blind = report[:-len(".md")] + "-blindness.txt"
    code, btext = git("show", f"HEAD:{blind}")
    if code != 0:
        return f"{blind} is not committed: nothing binds {report} to its registered round (row {i})"
    if not re.search(rf"^session id: {re.escape(want)}$", btext, re.M):   # the record's own line, never a substring
        return (f"{blind} does not name the session id row {i} derives ({want}): the reviewer it read was not the one "
                f"that round registered")
    # Pre-freeze review 5, M1 (lane fold5/report-binding; glitch-45's ruling 1, Sat 31 Oct 2026): the committed report
    # must be the bytes the reviewer's own session wrote, the sha256 its committed blindness record rebuilds from the
    # session file (review_kit/blindness.py, REPORT_DIGEST). Rounds 1-4 were committed before any record stated that
    # digest, so they are grandfathered by number, never by shape (REPORT_DIGEST_GRANDFATHERED).
    if n in REPORT_DIGEST_GRANDFATHERED:
        return None
    digest = _blindness().recorded_report_digest(btext)
    if digest is None:
        return (f"{blind} states no sha256 of the report as the reviewer's session wrote it: round {n} is after the "
                f"rule, so its report cannot seed the freeze unbound")
    raw = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{report}"], capture_output=True)
    got = hashlib.sha256(raw.stdout).hexdigest() if raw.returncode == 0 else None
    if got != digest:
        return (f"{report} at HEAD has sha256 {str(got)[:12]}, not the {digest[:12]} the reviewer's session wrote "
                f"({blind}): a report changed after its reviewer wrote it never seeds the freeze")
    return None


# Rounds whose blindness records predate the report digest (pre-freeze review 5, M1): review 4's report was masked by
# the Lane-orchestrator before commit (its as-written bytes are review_kit/prefreeze-4.as-written.md), and rounds 1-3
# were committed before the rule existed. None of them can seed a freeze now: grandfathered_seed_problem refuses each by
# number (pre-freeze review 6, M1), and later_review_problem refuses any seed with a later review registered or committed.
# Round 5 is not grandfathered: its committed blindness record predates section 8 and states no report digest, so
# registered_review_problem refuses it as a seed, and it ruled DO NOT FREEZE, which never seeds a freeze either way.
REPORT_DIGEST_GRANDFATHERED = (1, 2, 3, 4)


def _blindness():
    import importlib.util
    spec = importlib.util.spec_from_file_location("review_kit_blindness_for_freeze",
                                                  Path(__file__).resolve().parent / study.REVIEW_DIR / "blindness.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DUMMY_REVIEW = "0" * 40
DUMMY_PARENT = "0" * 40


def check_legs(draft) -> list[tuple[str, list[str]]]:
    """Pre-freeze review 1, m1: what --check reads, leg by leg, each with its problems ([] when it holds). It runs what a
    freeze runs short of the review and the write: the draft's PENDING map, the holdout fields, every pin (patterns
    expanded), the three vendor legs, the walk coverage of the arms the freeze runs, and prepare on a copy of the draft
    with a dummy review and a synthetic beacon reading (no network, nothing written)."""
    legs = [("copy manifest", copy_manifest.problems())]
    left = draft_pending(draft)
    legs.append(("pending", [f"{len(left)} PENDING input(s): " + ", ".join(left)] if left else []))
    problem = draft_holdout_problem(draft)
    legs.append(("holdout fields", [problem] if problem else []))
    try:
        paths = pinned_paths(PINNED)
        legs.append((f"pins ({len(paths)} paths, patterns expanded)", pin_problems([pin(p) for p in paths])))
    except ValueError as e:
        legs.append(("pins", [str(e)]))
    problem = unrecorded_shapes_problem(draft)
    legs.append(("vendor legs i-iii", [problem] if problem else []))
    problem = coverage_problem(draft)
    legs.append(("walk coverage of the arms the freeze runs", [problem] if problem else []))
    problem = order_function_problem(draft)          # pre-freeze review 2, m3
    legs.append(("take-order function", [problem] if problem else []))
    try:
        reading = synthetic_beacon_reading(order_beacon.registered_round(draft.get(BEACON_KEY)))
        prepare(copy.deepcopy(draft), review=DUMMY_REVIEW, parent=DUMMY_PARENT, pins=[], frozen_at="check",
                beacon=reading)
        legs.append(("prepare (dummy review, synthetic beacon reading)", []))
    except Exception as e:      # noqa: BLE001 (every refusal of prepare is this leg's finding, by name)
        legs.append(("prepare (dummy review, synthetic beacon reading)", [f"{type(e).__name__}: {e}"]))
    return legs


def check() -> int:
    """freeze.py --check: every leg of check_legs printed, exit 1 when any has a problem."""
    draft = json.loads(DRAFT.read_text())
    legs = check_legs(draft)
    for name, problems in legs:
        print(f"freeze --check: {name}: " + ("ok" if not problems else "FAIL " + "; ".join(problems)[:1500]))
    entries, _ = copy_manifest.load_fragments()
    claimed = sum(1 for _, e in entries if e["status"] in copy_manifest.STATUSES)
    try:
        paths = pinned_paths(PINNED)
    except ValueError:
        paths = []
    readers = sum(1 for p in paths if copy_manifest.READER_RECORD.fullmatch(p[len(study.STUDY_REL) + 1:]))
    bad = sum(1 for _, problems in legs if problems)
    print(f"freeze: {claimed} fragment-claimed files and {readers} native-reader record(s) owned; "
          f"{len(legs) - bad} of {len(legs)} legs hold; no takes or freeze performed")
    return 1 if bad else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Freeze the full round 4 design once")
    parser.add_argument("--review-commit")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--rehearsal-record", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--holdout-digests", type=Path)
    parser.add_argument("--beacon-reading", type=Path,
                        help="a disposable rehearsal only: a reading of the registered drand round, checked offline")
    args = parser.parse_args(argv)
    try:
        if args.check:
            return check()
        problems = copy_manifest.problems()
        if problems:
            raise ValueError("; ".join(problems))
        problem = holdout_source_problem(args.holdout_digests, args.rehearsal)
        if problem:
            raise ValueError(problem)
        if not args.review_commit:
            raise ValueError("a committed pre-freeze review is required")
        if outputs_exist(HERE):
            raise ValueError("a freeze output already exists; the freeze happens once")
        if args.rehearsal:
            code, remotes = git("remote")
            if code or remotes:
                raise ValueError("rehearsal requires a throwaway clone without remotes")
        code, dirty = git("status", "--porcelain")
        if code or dirty:
            raise ValueError("the complete repository must be committed before freezing")
        bad, review_file = review_file_problems(args.review_commit)
        if bad:
            raise ValueError("; ".join(bad))
        draft = json.loads(DRAFT.read_text())
        problem = draft_holdout_problem(draft)
        if problem:
            raise ValueError(problem)
        problem = unrecorded_shapes_problem(draft)
        if problem:
            raise ValueError(problem)
        problem = order_function_problem(draft)      # pre-freeze review 2, m3
        if problem:
            raise ValueError(problem)
        holdout = ({} if args.holdout_digests is None else
                   holdout_fields(args.holdout_digests, [task["id"] for task in draft["tasks"]],
                                  rehearsal=args.rehearsal))
        digest = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
        tree = study_tree_sha()
        record = None
        if args.write and not args.rehearsal:
            record = rehearsal_evidence(args.rehearsal_record, digest, tree)
        pins = [pin(p) for p in pinned_paths(PINNED)]
        bad = pin_problems(pins)
        if bad:
            raise ValueError("every owned build file must have a committed pin: " + "; ".join(bad[:6]))
        problem = coverage_problem(draft)
        if problem:
            raise ValueError(problem)
        witness = WITNESS_NOT_REHEARSED if args.rehearsal else take_order_witness(draft)
        beacon = take_order_beacon_reading(draft, rehearsal=args.rehearsal, reading_file=args.beacon_reading)
        _, parent = git("rev-parse", "HEAD")
        frozen = prepare(draft, review=args.review_commit, parent=parent, pins=pins,
                         frozen_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(), beacon=beacon)
        frozen.update(draft_sha256_at_freeze=digest, pre_freeze_review_file=review_file,
                      pre_freeze_review_sha256=hashlib.sha256((REPO / review_file).read_bytes()).hexdigest(),
                      rehearsal_record=record if record else "rehearsal or preview",
                      rehearsed_study_tree_sha256=tree, take_order_witness=witness)
        frozen.update(holdout)
        if not holdout:
            print(HOLDOUT_NOT_REHEARSED)
        if keys_outside_the_freeze(draft, frozen):
            raise ValueError("freeze changed the registered design")
        if args.write:
            outputs = write_outputs(frozen)
            print("freeze: wrote " + ", ".join(p.name for p in outputs) + "; commit all three in one commit")
        else:
            print(json.dumps(frozen, indent=2))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f"freeze: REFUSE: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
