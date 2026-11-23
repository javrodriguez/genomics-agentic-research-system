#!/usr/bin/env python3
"""Lane pf1-checker-digest (Gap Study round 4, fold plan prefreeze-1 MAJOR 4 and section 3; the lane orchestrator's
assignment of Sun 25 Oct 2026 under Javier's standing delegation): the digest a walk is checked under binds the
checker's code as well as its constants.

The finding (a read-only analysis of 25 Oct 2026, reproduced on the freeze line 166f8fa8): w135-w168's check.json
carry the constants digest in force today, yet session_store_problems (9e57ce79, 16 Oct) and
transcript_content_problems (lane pf1-l3, 24 Oct) were added after w135 was checked, so w165 counted as covered off a
check.json with no reasons while a recheck today gives it two nested-agent reasons. checker_constants_sha256 hashed
CHECKER_CONSTANTS alone, so a code-only checker change marked nothing stale.

The rule (check_take B7): checker_constants_sha256 is the sha256 of {"checker_code_sha256", "constants_sha256"}, the
code half the sha256 of every CHECKER_CODE_FILES file's git blob id as its bytes stand under CHECKER_CODE_ROOT. The
bytes are hashed whole, so a comment-only edit to a bound file makes a walk stale too (a recheck is a re-derivation
from committed bytes, no model and no money: fail closed is cheap); a file outside the list moves nothing.

  D1-pin       CHECKER_CODE_FILES is exactly the rule's set, derived here from the source by ast: check_take.py, every
               study module it imports (module or function level), every module those import at module level,
               transitively; plus drive.py (take_checker, the checker's call site, adds readers-disagree),
               vendor_provenance.py (mode_binding.argv_mode calls it while check_take reads a vendor walk's mode),
               routing.json (the operator vocabulary and the reasons that become events) and the README.md of each
               recorded fixture folder VENDOR_READER_ITEMS and VENDOR_PENDING_ROWS name (the vendor check reads its
               RECORDED labels). And the function-level
               imports those modules make outside the set are exactly LAZY_OUTSIDE, each named not checking (D2
               shows none of them runs).
  D2-run       checking committed walks of each harness (w165 claude-code, w-o46 codex, w-g21 gemini) through
               drive.take_checker runs code from listed files only and opens no study file outside the list.
  D3-git       each manifest entry is git's own blob id: `git hash-object --no-filters` of the file, and `git ls-tree`
               of a commit holding the files, so the digest re-derives from git at HEAD in a clean checkout.
  D4-code      a code-only change to a checking function (session_store_problems) makes a graded walk checked under
               the old code stale, for claude-code and for a vendor walk's merged digest; undoing it restores the
               walk's standing (the digest is a function of the bytes, nothing else).
  D5-comment   a comment-only change to a bound file makes the walk stale (the rule above, stated).
  D6-other     a change to a file outside the list (walk_plan.py, result.py) leaves the walk counted.
  D7-shape     checker_constants_sha256 is the canonical-JSON sha256 of exactly its two halves, recomputed here from
               the files; constants_only_sha256 keeps B5's constants-only rule; a listed file missing, or a link,
               refuses (CheckRefused), never a digest over fewer files.
  D8-regrade   the vendor regrade reads no checker digest: regrade_doc of committed pending walks w-o46 and w-g21,
               made with checker_constants_sha256, constants_only_sha256, checker_code_sha256 and
               checker_code_manifest all raising, completes, grades the walk and records no digest.
  D11-cache    the blob-id cache: with an injected clock that lets every file settle, an edit to a cached listed file
               still moves the digest; with the real clock, a file written just now is never remembered.
  D9-witness   each mutant below turns its case red.
  D10-writers  what a checked walk records (the claude-code side's and the vendor side's digest, which walk_regrade's
               recheck also writes) is what coverage reads as in force, and both move with the code.

The fold of review c99f114 (the lane orchestrator's rulings of Mon 26 Oct 2026):
  MAJOR 1      option (a), narrowly: the design road's inputs the checker's reasons read are bound too. The list
               gains every tasks/*.json and variants/*.json (design_view reads its task's pair) and the graders
               design_view loads by name (DESIGN_GRADERS, their module-level imports followed); a third part,
               design_values_sha256, binds only the pre-registration in force's leak_words and leak_context_excusals
               values, so a regenerated draft moves nothing (D6-draft). D4 adds a task edit, a variants edit and
               each leak value's edit; D2 now builds every task's and harness's view inside its window
               (production_design, the call walk_builders' design_for makes) and the checker's own view too.
  MINOR 1      check_results.py is bound (takes.load_rows' validate_ledger on the take road).
  MINOR 2      D13: the stale message says "checker constants or code"; walk_regrade's no-digest refusal names a
               missing code file.
  NIT 1        the vendor writer's mutant is pinned.
  D12          run_checks: the battery command, and only it, runs under BATTERY_TIMEOUT_S (7200 s).
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

ct = pw = None
STUDY = "evals/gap-study-4/"
EXTRAS = (STUDY + "drive.py", STUDY + "vendor_provenance.py", STUDY + "routing.json",
          STUDY + "check_results.py")      # review c99f114 MINOR 1: takes.load_rows' validate_ledger, the take road
# Review c99f114 MAJOR 1: the graders design_view loads by name (variants.load_grader) while it builds a walk's or a
# take's view; each one's module-level imports are followed as check_take's are. D2 profiles the design road over a
# row of every task and harness, so a grader loaded there and missing here goes red.
DESIGN_GRADERS = tuple(STUDY + f"graders/{g}.py" for g in ("confounded_design", "new_tasks", "precondition_refusal",
                                                          "scope_read", "template_adherence"))
# Function-level imports in bound modules (other than check_take.py) that leave the set: none of them runs while a
# walk or a take is checked or its design view built (D2 profiles walks of each harness and the design road), so none
# is bound. A new one fails D1 until it is classified here or bound. check_results.py is bound as one file: its own
# imports (freeze, result and the rest) are not followed, because validate_ledger only refuses a malformed ledger.
LAZY_OUTSIDE = {
    (STUDY + "batch.py", "costs"), (STUDY + "batch.py", "run_builders"),
    (STUDY + "box/run_take.py", "box.preflight"),
    (STUDY + "drive.py", "walk_register"), (STUDY + "drive.py", "box.ownership"),
    (STUDY + "drive.py", "box.settings_guard"), (STUDY + "drive.py", "fixtures.gen_explain_not_act"),
    (STUDY + "prereg.py", "freeze"), (STUDY + "prereg.py", "order_beacon"),
    (STUDY + "takes.py", "run"),
    (STUDY + "check_results.py", "freeze"), (STUDY + "check_results.py", "labelling.sample"),
    (STUDY + "check_results.py", "result"), (STUDY + "check_results.py", "run_builders"),
    (STUDY + "check_results.py", "build_draft"), (STUDY + "check_results.py", "order_beacon"),     # lane fold11: the recheck
}
WALKS = ("w165", "w-o46", "w-g21")
PENDING_WALKS = ("w-o46", "w-g21")


def setUpModule():
    global ct, pw
    saved = list(sys.path)
    import check_take as ct
    import pending_walk as pw
    sys.path[:] = saved


# ---- D1: the rule, derived from the source --------------------------------------------------------------------------

def _resolve(name: str):
    for root in (REPO / "evals/gap-study-4", REPO / "evals"):
        p = root.joinpath(*name.split("."))
        if p.with_suffix(".py").is_file():
            return p.with_suffix(".py")
        if (p / "__init__.py").is_file():
            return p / "__init__.py"
    return None


def _imports(path: Path, *, module_level_only: bool) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in (tree.body if module_level_only else ast.walk(tree)):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names |= {node.module} | {f"{node.module}.{a.name}" for a in node.names}
    return names


def fixture_readmes(mod) -> set:
    """The README.md of each recorded fixture folder the vendor reader items and rows name."""
    named = [f for items in mod.VENDOR_READER_ITEMS.values() for f in items.values() if isinstance(f, str)]
    named += [r["fixture"] for rows in mod.VENDOR_PENDING_ROWS.values() for r in rows.values()
              if isinstance(r, dict) and isinstance(r.get("fixture"), str)]
    return {f"{STUDY}tests/fixtures/{f.split('/')[0]}/README.md" for f in named}


def design_files() -> set:
    """Review c99f114 MAJOR 1: every task file and variants file design_view reads (variants.load_task and
    variants.operator_steps read tasks/<task>.json and variants/<task>.json)."""
    return {p.relative_to(REPO).as_posix() for d in ("tasks", "variants") for p in (REPO / STUDY / d).glob("*.json")}


def rule_set(mod=None) -> set:
    seen, todo = set(), [(REPO / STUDY / "check_take.py", False)] + [(REPO / g, True) for g in DESIGN_GRADERS]
    while todo:
        path, top = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        todo += [(p, True) for n in _imports(path, module_level_only=top) for p in (_resolve(n),) if p]
    return {p.relative_to(REPO).as_posix() for p in seen} | set(EXTRAS) | fixture_readmes(mod or ct) | design_files()


def lazy_outside(files) -> set:
    out = set()
    for rel in files:
        if not rel.endswith(".py") or rel == STUDY + "check_take.py":
            continue
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        top = {id(n) for n in tree.body}
        for node in ast.walk(tree):
            if id(node) in top or not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                ([node.module] + [f"{node.module}.{a.name}" for a in node.names]
                 if node.level == 0 and node.module else [])
            for n in names:
                p = _resolve(n)
                if p and p.relative_to(REPO).as_posix() not in files:
                    out.add((rel, n))
    return out


def pin_problems(mod) -> list:
    files = tuple(mod.CHECKER_CODE_FILES)
    out = []
    if list(files) != sorted(set(files)):
        out.append("D1-pin: CHECKER_CODE_FILES is not sorted and distinct")
    want = rule_set(mod)
    if set(files) != want:
        out.append(f"D1-pin: missing {sorted(want - set(files))}, extra {sorted(set(files) - want)}")
    got = lazy_outside(set(files))
    if got != LAZY_OUTSIDE:
        out.append(f"D1-pin: lazy imports leaving the set: new {sorted(got - LAZY_OUTSIDE)}, "
                   f"gone {sorted(LAZY_OUTSIDE - got)}")
    return out


# ---- a copy of the bound code to edit, and a graded walk checked under it -------------------------------------------

class CodeTree:
    """The bound files (and two unbound ones) copied under a temporary root, as CHECKER_CODE_ROOT."""

    UNBOUND = (STUDY + "walk_plan.py", STUDY + "result.py")

    def __init__(self, mod):
        self.root = Path(tempfile.mkdtemp(prefix="pf1-digest-code-"))
        for rel in tuple(mod.CHECKER_CODE_FILES) + self.UNBOUND:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / rel, self.root / rel)
        # review c99f114 MAJOR 1: a copy of the pre-registration in force, as DESIGN_VALUES_PATH
        import prereg
        self.prereg = self.root / "prereg-in-force.json"
        shutil.copyfile(prereg.in_force(), self.prereg)

    def edit_prereg(self, change):
        doc = json.loads(self.prereg.read_text(encoding="utf-8"))
        change(doc)
        self.prereg.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")   # another layout as well

    def restore_prereg(self):
        import prereg
        shutil.copyfile(prereg.in_force(), self.prereg)

    def edit(self, rel: str, old: str, new: str, *, after: str = ""):
        p = self.root / rel
        src = p.read_text(encoding="utf-8")
        at = src.index(after) if after else 0
        i = src.index(old, at)
        p.write_text(src[:i] + new + src[i + len(old):], encoding="utf-8")

    def restore(self, rel: str):
        shutil.copyfile(REPO / rel, self.root / rel)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


AGENTS = {"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0},
          "nested_cli_calls": 0}


def world(digest: str, harness=None) -> Path:
    base = Path(tempfile.mkdtemp(prefix="pf1-digest-walk-")) / "rehearsals"
    folder = base / "w-digest"
    folder.mkdir(parents=True)
    (folder / "grade.json").write_text(json.dumps({"graded": True, "row": {}, "grade": {}}))
    (folder / "check.json").write_text(json.dumps(dict(
        {"walk": "w-digest", "checked": True, "checker_reasons": [], "events": {"outside_reach": 0},
         "route": "graded", "route_refused": None, "checker_constants_sha256": digest, "no_output_nudges": 0},
        **AGENTS)))
    if harness:
        (folder / "driver-ledger.json").write_text(json.dumps({"agent": {"harness": harness}}))
    return base


SESSION_STORE = "def session_store_problems(path: Path) -> list:"
CODE_EDIT = ('    own = led.get("session_id")\n', '    own = led.get("session_id") or None\n')
COMMENT_EDIT = ('    led = _ledger_beside(path) or {}\n', '    led = _ledger_beside(path) or {}\n    # a comment\n')


def standing_cases(mod=None, pmod=None) -> list:
    """D4, D5, D6 on a claude-code walk and a codex walk; the problem lines, empty when all hold."""
    mod = mod or ct
    pmod = pmod or pw
    out = []
    tree = CodeTree(mod)
    bases = []
    try:
        with mock.patch.object(mod, "CHECKER_CODE_ROOT", tree.root), \
                mock.patch.object(mod, "DESIGN_VALUES_PATH", tree.prereg), \
                mock.patch.dict(sys.modules, {"check_take": mod}):
            for harness in (None, "codex"):
                digest = mod.vendor_checker_constants_sha256(harness) if harness else mod.checker_constants_sha256()
                base = world(digest, harness)
                bases.append(base)
                tag = harness or "claude-code"

                def standing():
                    return pmod.checker_standing(base, "w-digest")
                if standing() is not None:
                    out.append(f"{tag}: a walk checked under the code in force is not counted: {standing()!r}")
                for name, (old, new), want_stale in (("D4-code", CODE_EDIT, True), ("D5-comment", COMMENT_EDIT, True)):
                    tree.edit(STUDY + "check_take.py", old, new, after=SESSION_STORE)
                    got = standing()
                    if want_stale != (isinstance(got, str) and got.startswith("stale")):
                        out.append(f"{name} {tag}: standing {got!r} after the edit")
                    tree.restore(STUDY + "check_take.py")
                    if standing() is not None:
                        out.append(f"{name} {tag}: undoing the edit does not restore the walk: {standing()!r}")
                for rel in CodeTree.UNBOUND:
                    tree.edit(rel, "\n", "\n# an edit outside the bound code\n")
                    if standing() is not None:
                        out.append(f"D6-other {tag}: an edit to {rel} moved the digest: {standing()!r}")
                    tree.restore(rel)
                # review c99f114 MAJOR 1: a task file, a variants file and each bound pre-registration value
                for name, edit in (("D4-task", lambda: tree.edit(STUDY + "tasks/plan-gate.json", "{", "{ ")),
                                   ("D4-variants", lambda: tree.edit(STUDY + "variants/plan-gate.json", "{", "{ ")),
                                   ("D4-leak-words", lambda: tree.edit_prereg(
                                       lambda d: d["leak_words"].append("zz-a-new-leak-word"))),
                                   ("D4-leak-excusals", lambda: tree.edit_prereg(
                                       lambda d: d["leak_context_excusals"].pop()))):
                    edit()
                    got = standing()
                    if not (isinstance(got, str) and got.startswith("stale")):
                        out.append(f"{name} {tag}: standing {got!r} after the edit")
                    tree.restore(STUDY + "tasks/plan-gate.json")
                    tree.restore(STUDY + "variants/plan-gate.json")
                    tree.restore_prereg()
                    if standing() is not None:
                        out.append(f"{name} {tag}: undoing the edit does not restore the walk: {standing()!r}")
                # the draft regenerated (another layout, another key, another value of an unbound key) moves nothing
                tree.edit_prereg(lambda d: d.update(pf1_digest_probe="regenerated", walk_counts={"probe": 1}))
                if standing() is not None:
                    out.append(f"D6-draft {tag}: a regenerated draft with the same leak values moved the digest: "
                               f"{standing()!r}")
                tree.restore_prereg()
    finally:
        tree.close()
        for b in bases:
            shutil.rmtree(b.parent, ignore_errors=True)
    return out


def shape_problems(mod=None) -> list:
    """D7: the two halves recomputed here; a missing or linked listed file refuses."""
    mod = mod or ct
    out = []
    lines = {}
    for rel in mod.CHECKER_CODE_FILES:
        raw = (REPO / rel).read_bytes()
        lines[rel] = hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
    code = hashlib.sha256(json.dumps(lines, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    consts = hashlib.sha256(json.dumps(mod.CHECKER_CONSTANTS, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode("utf-8")).hexdigest()
    import prereg
    doc = json.loads(prereg.in_force().read_text(encoding="utf-8"))
    values = {"leak_context_excusals": doc.get("leak_context_excusals"), "leak_words": doc.get("leak_words")}
    design = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode("utf-8")).hexdigest()
    want = hashlib.sha256(json.dumps({"checker_code_sha256": code, "constants_sha256": consts,
                                      "design_values_sha256": design}, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()
    with mock.patch.object(mod, "CHECKER_CODE_ROOT", REPO), mock.patch.object(mod, "DESIGN_VALUES_PATH", None):
        if mod.checker_code_manifest() != lines:
            out.append("D7-shape: the manifest is not each file's git blob id")
        if mod.checker_code_sha256() != code:
            out.append("D7-shape: checker_code_sha256 is not the sha256 of the manifest")
        if mod.constants_only_sha256() != consts:
            out.append("D7-shape: constants_only_sha256 is not B5's constants-only digest")
        if mod.design_values() != values or mod.design_values_sha256() != design:
            out.append("D7-shape: the design values are not exactly the in-force leak_words and leak_context_excusals")
        if mod.checker_constants_sha256() != want:
            out.append("D7-shape: checker_constants_sha256 is not the sha256 of its three parts")
    tree = CodeTree(mod)
    try:
        with mock.patch.object(mod, "CHECKER_CODE_ROOT", tree.root):
            for how in ("missing", "link"):
                p = tree.root / STUDY / "routing.py"
                p.unlink()
                if how == "link":
                    p.symlink_to(REPO / STUDY / "routing.py")
                try:
                    got = mod.checker_constants_sha256()
                    out.append(f"D7-shape: a {how} listed file gave a digest {got[:12]}")
                except mod.CheckRefused:
                    pass
                if p.is_symlink() or p.exists():
                    p.unlink()
                tree.restore(STUDY + "routing.py")
            with mock.patch.object(mod, "DESIGN_VALUES_PATH", tree.root / "no-prereg.json"):
                try:
                    got = mod.checker_constants_sha256()
                    out.append(f"D7-shape: a missing pre-registration gave a digest {got[:12]}")
                except mod.CheckRefused:
                    pass
    finally:
        tree.close()
    return out


def writer_problems(mod=None) -> list:
    """D10: what a checked walk records (the claude-code side's design_constants_sha256, the vendor side's
    vendor_design_constants_sha256, both walk_regrade's recheck digest too) is what coverage reads as in force
    (checker_constants_sha256, vendor_checker_constants_sha256), and both move with the code."""
    import copy
    mod = mod or ct
    out = []
    pre = copy.deepcopy(mod.CHECKER_CONSTANTS)
    pre["driver_constants"]["permission_mode_by_arm"] = {"A": "bypassPermissions"}
    # merge lane L6c: the writer binds the view's own design values, so the rig's view carries the in-force ones, as
    # design_view's (from prereg.load()) does
    claude = mod.Design(task_id="t", spec={}, pre=dict(pre, **mod.design_values()), harness="claude-code")
    codex = mod.vendor_view(claude.replace(harness="codex"))
    tree = CodeTree(mod)
    try:
        with mock.patch.object(mod, "CHECKER_CODE_ROOT", tree.root):
            before = (mod.design_constants_sha256(claude), mod.vendor_design_constants_sha256(codex))
            tree.edit(STUDY + "check_take.py", *CODE_EDIT, after=SESSION_STORE)
            for name, wrote, read, old in (
                    ("claude-code", mod.design_constants_sha256(claude), mod.checker_constants_sha256(), before[0]),
                    ("codex", mod.vendor_design_constants_sha256(codex), mod.vendor_checker_constants_sha256("codex"),
                     before[1])):
                if wrote != read:
                    out.append(f"D10-writers {name}: the side records {wrote} and coverage reads {read} in force")
                if wrote == old:
                    out.append(f"D10-writers {name}: the recorded digest did not move with the code")
    finally:
        tree.close()
    return out


def cache_problems(mod=None) -> list:
    """D11: the blob-id cache. With an injected clock that lets every file settle, an edit to a listed file still
    moves the digest (the signature is read); with the real clock, a file written within CODE_CACHE_SETTLE_NS is
    never remembered."""
    mod = mod or ct
    out = []
    tree = CodeTree(mod)
    try:
        with mock.patch.object(mod, "CHECKER_CODE_ROOT", tree.root):
            with mock.patch.object(mod, "_now_ns", lambda: 1 << 62):
                first = mod.checker_constants_sha256()
                tree.edit(STUDY + "routing.py", "\n", "\n# an edit after the cache filled\n")
                if mod.checker_constants_sha256() == first:
                    out.append("D11-cache: a cached file's edit did not move the digest")
                tree.restore(STUDY + "routing.py")
                if mod.checker_constants_sha256() != first:
                    out.append("D11-cache: undoing the edit did not restore the digest")
                with mock.patch.object(mod, "DESIGN_VALUES_PATH", tree.prereg):
                    held = mod.checker_constants_sha256()
                    tree.edit_prereg(lambda d: d["leak_words"].append("zz-cache-probe"))
                    if mod.checker_constants_sha256() == held:
                        out.append("D11-cache: a cached pre-registration's leak-word edit did not move the digest")
                    tree.restore_prereg()
            mod._CODE_CACHE.clear()
            mod._CODE_HALF_CACHE.clear()
            tree.edit(STUDY + "routing.py", "\n", "\n# a fresh edit\n")
            mod.checker_constants_sha256()
            if str((tree.root / STUDY / "routing.py").absolute()) in mod._CODE_CACHE:
                out.append("D11-cache: a file written just now was remembered")
            if any(k[0] == str(tree.root.absolute()) for k in mod._CODE_HALF_CACHE):
                out.append("D11-cache: a code half over a file written just now was remembered")
    finally:
        tree.close()
        mod._CODE_CACHE.clear()
        mod._CODE_HALF_CACHE.clear()
    return out


def regrade_problems(wmod=None, *, first=False) -> list:
    """D8: each committed pending walk's regrade, made with every checker digest function raising, completes and
    grades the walk; `first` stops at the first problem (the witness)."""
    import walk_regrade
    wmod = wmod or walk_regrade
    out = []

    def boom(*a, **k):
        raise AssertionError("the regrade read a checker digest")
    for walk in PENDING_WALKS:
        with mock.patch.object(ct, "checker_constants_sha256", boom), \
                mock.patch.object(ct, "checker_code_sha256", boom), \
                mock.patch.object(ct, "checker_code_manifest", boom), \
                mock.patch.object(ct, "constants_only_sha256", boom):
            try:
                doc = wmod.regrade_doc(walk, HERE)
                if doc.get("graded") is not True:
                    out.append(f"D8-regrade {walk}: the regrade did not grade it: {str(doc.get('why'))[:200]}")
                if b"checker_constants_sha256" in wmod.regrade_bytes(doc):
                    out.append(f"D8-regrade {walk}: the regrade records a checker digest")
            except Exception as e:  # noqa: BLE001 - a regrade that reaches a digest raises
                out.append(f"D8-regrade {walk}: {type(e).__name__}: {e}")
        if out and first:
            break
    return out


def mutant(mod, old: str, new: str):
    src = Path(mod.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutant anchor found {src.count(old)} times: {old!r}")
    m = types.ModuleType(mod.__name__)
    m.__file__ = mod.__file__
    with mock.patch.dict(sys.modules, {mod.__name__: m}):
        exec(compile(src.replace(old, new), mod.__file__, "exec"), m.__dict__)
    return m


def run_checks_problems(mod=None) -> list:
    """D12 (the lane orchestrator's ruling on review c99f114's test_round4 note): the battery command, and only it,
    runs under BATTERY_TIMEOUT_S (7200 s); every other command keeps TIMEOUT_S (3600 s). Shown on run_all itself with
    both limits shrunk: a 2 s battery passes under a 6 s battery limit while a 2 s lane command times out at 1 s."""
    import io
    from contextlib import redirect_stdout
    import run_checks
    mod = mod or run_checks
    out = []
    if (mod.TIMEOUT_S, mod.BATTERY_TIMEOUT_S, mod.POST_RUN_TIMEOUT_S) != (3600, 18000, 14400):
        out.append(f"D12-timeout: the limits are {(mod.TIMEOUT_S, mod.BATTERY_TIMEOUT_S, mod.POST_RUN_TIMEOUT_S)}, "
                   f"not (3600, 18000, 14400)")
    if mod.POST_RUN_LINES != frozenset(('pf1-l2b-labelling-stats.txt:5', 'w4e-cp5-stats.txt:3', 'w4e-cp5-stats.txt:4', 'w5b-cp5-pipeline.txt:8', 'w5b-cp5-pipeline.txt:10', 'w5b-cp5-pipeline.txt:12', 'w5c-draft-ci.txt:9', 'w5c-draft-ci.txt:10', 'w5c-draft-ci.txt:11', 'w5c-draft-ci.txt:12', 'w5c-draft-ci.txt:13', 'w5c-draft-ci.txt:14', 'w5c-draft-ci.txt:15', 'w5c-draft-ci.txt:16')):
        out.append("D12-timeout: the post-run lines are not the ones v3-timeouts named")
    if any(mod.timeout_for(w) != mod.POST_RUN_TIMEOUT_S for w in mod.POST_RUN_LINES):
        out.append("D12-timeout: a post-run line is not run under POST_RUN_TIMEOUT_S")
    if mod.timeout_for("test_round4") != mod.BATTERY_TIMEOUT_S:
        out.append("D12-timeout: the battery is not run under BATTERY_TIMEOUT_S")
    if any(mod.timeout_for(w) != mod.TIMEOUT_S for w in ("pf1-checker-digest.txt:5", "test_round4.py", "x")):
        out.append("D12-timeout: a command other than the battery is not run under TIMEOUT_S")
    battery = "sleep 2; echo 'test_round4: 1 run, 0 skipped, 0 expected failures'"
    with mock.patch.object(mod, "TIMEOUT_S", 1), mock.patch.object(mod, "BATTERY_TIMEOUT_S", 6), \
            redirect_stdout(io.StringIO()) as log:
        got = mod.run_all([("test_round4", battery), ("lane.txt:1", "sleep 2")])
    text = log.getvalue()
    if got != (1, 2) or "PASS [test_round4]" not in text or "FAIL [lane.txt:1] exit timeout" not in text \
            or "no result within 1 s" not in text:
        out.append(f"D12-timeout: run_all gave {got}: {text.strip()[-300:]!r}")
    return out


CT_MUTANTS = (
    ("binding-dropped",
     "    return _bound_digest(constants_only_sha256(constants), checker_code_sha256(), design_values_sha256())",
     "    return constants_only_sha256(constants)", "standing"),
    ("design-values-dropped",
     "    return _bound_digest(constants_only_sha256(constants), checker_code_sha256(), design_values_sha256())",
     "    return _bound_digest(constants_only_sha256(constants), checker_code_sha256(), '')", "standing"),
    ("one-design-value-dropped", 'DESIGN_VALUE_KEYS = ("leak_context_excusals", "leak_words")',
     'DESIGN_VALUE_KEYS = ("leak_words",)', "standing"),
    ("whole-draft-bound", "    return {k: doc.get(k) for k in DESIGN_VALUE_KEYS}", "    return doc", "standing"),
    ("vendor-writer-constants-only",       # merge lane L6c: the writer's line is view_checker_constants_sha256's
     '        got["driver_constants"].pop("permission_mode_by_arm", None)\n'
     '        return view_checker_constants_sha256(got, design)\n'
     '    except (KeyError, TypeError, AttributeError, CheckRefused):\n        return None\n\n\ndef checker_view(',
     '        got["driver_constants"].pop("permission_mode_by_arm", None)\n        return constants_only_sha256(got)\n'
     '    except (KeyError, TypeError, AttributeError, CheckRefused):\n        return None\n\n\ndef checker_view(',
     "writers"),
    ("bytes-not-hashed", "    blob = git_blob_id(p.read_bytes())", "    blob = git_blob_id(str(p).encode())",
     "standing"),
    ("cache-ignores-signature", "    if hit is not None and hit[0] == sig:", "    if hit is not None:", "cache"),
    ("fresh-file-cached", "    if _now_ns() - max(st.st_mtime_ns, st.st_ctime_ns) > CODE_CACHE_SETTLE_NS:",
     "    if True:", "cache"),
    ("half-cache-ignores-signatures", "    key = (str(root.absolute()), tuple(sigs)) if sigs is not None else None",
     "    key = (str(root.absolute()),) if sigs is not None else None", "cache"),
    ("fresh-half-cached",
     "    if key is not None and _now_ns() - max(max(s[3], s[4]) for s in sigs) > CODE_CACHE_SETTLE_NS:",
     "    if key is not None:", "cache"),
    ("design-cache-ignores-signature", "    if sig is not None and hit is not None and hit[0] == sig:",
     "    if hit is not None:", "cache"),
    ("file-dropped", '    "evals/gap-study-4/drive.py",\n', "", "pin"),
    ("missing-file-skipped", "            raise CheckRefused(f\"the checker's code file {rel} is missing or a link",
     "            continue\n            raise CheckRefused(f\"the checker's code file {rel} is missing or a link",
     "shape"),
    ("blob-header-dropped", '    return hashlib.sha1(b"blob %d\\0" % len(raw) + raw).hexdigest()',
     "    return hashlib.sha1(raw).hexdigest()", "shape"),
    ("claude-writer-constants-only",       # merge lane L6c: as vendor-writer-constants-only
     '        got["driver_constants"].pop("permission_mode_by_arm", None)\n'
     '        return view_checker_constants_sha256(got, design)\n'
     '    except (KeyError, TypeError, AttributeError, CheckRefused):\n        return None\n\n\n# ---- B7',
     '        got["driver_constants"].pop("permission_mode_by_arm", None)\n        return constants_only_sha256(got)\n'
     '    except (KeyError, TypeError, AttributeError, CheckRefused):\n        return None\n\n\n# ---- B7', "writers"),
    ("vendor-reader-constants-only", "    return checker_constants_sha256(vendor_constants(harness, constants, block))",
     "    return constants_only_sha256(vendor_constants(harness, constants, block))", "standing"),
)
WR_MUTANTS = (
    ("regrade-reads-the-digest", '        doc = {"schema": 1, "walk": walk, "walk_commit"',
     '        doc = {"schema": 1, "checker_constants_sha256": __import__("check_take").checker_constants_sha256(), '
     '"walk": walk, "walk_commit"'),
)
RC_MUTANTS = (
    ("battery-on-the-common-timeout", "        return BATTERY_TIMEOUT_S\n", "        return TIMEOUT_S\n"),
    ("every-command-on-the-battery-timeout",
     "    return POST_RUN_TIMEOUT_S if where in POST_RUN_LINES else TIMEOUT_S", "    return BATTERY_TIMEOUT_S"),
    ("every-command-on-the-post-run-timeout",
     "    return POST_RUN_TIMEOUT_S if where in POST_RUN_LINES else TIMEOUT_S", "    return POST_RUN_TIMEOUT_S"),
    ("post-run-lines-on-the-common-timeout",
     "    return POST_RUN_TIMEOUT_S if where in POST_RUN_LINES else TIMEOUT_S", "    return TIMEOUT_S"),
    ("run-all-on-the-common-timeout", "text=True, errors=\"replace\", timeout=timeout_for(where))",
     "text=True, errors=\"replace\", timeout=TIMEOUT_S)"),
)


class TheCheckerCodeDigest(unittest.TestCase):
    def test_d1_the_list_is_the_rule(self):
        self.assertEqual(pin_problems(ct), [])

    def test_d2_checking_runs_and_opens_listed_files_only(self):
        """The design road (walk_regrade.production_design, the same call walk_builders' design_for makes: checker_view
        of design_view with batch.expected_pin) over the first registered walk of every task and harness, then the
        checker on w165, w-o46 and w-g21 with its design built inside the window too: only listed code runs, and only
        listed files and the pre-registration in force (bound by its two values) are opened. prereg.load()'s cache is
        dropped first so its read is seen."""
        import drive
        import prereg
        import run as run_mod
        import walk_regrade as wr
        root, prefix = wr._repo(HERE)
        reg = json.loads((HERE / "rehearsals" / "register.json").read_text())
        bound = {str(REPO / rel) for rel in ct.CHECKER_CODE_FILES}
        draft = str(prereg.in_force().resolve())
        me = str(Path(__file__).resolve())
        builder = (str(Path(wr.__file__).resolve()), "production_design")      # the call itself, three lines
        ran, opened = set(), set()
        state = {"on": False, "tmp": "/nonexistent-pf1"}

        def prof(frame, event, arg):
            if event == "call" and state["on"]:
                ran.add((frame.f_code.co_filename, frame.f_code.co_name))

        def audit(event, args):
            if event == "open" and state["on"] and isinstance(args[0], (str, Path)) \
                    and not str(args[0]).startswith(state["tmp"]):
                opened.add(str(Path(args[0]).resolve()))
        sys.addaudithook(audit)

        def window(fn):
            saved, prereg._cache = prereg._cache, None
            state["on"] = True
            sys.setprofile(prof)
            try:
                return fn()
            finally:
                sys.setprofile(None)
                state["on"] = False
                prereg._cache = saved
        firsts = {}
        for e in reg["walks"]:
            ledger = json.loads((HERE / "rehearsals" / e["walk"] / drive.LEDGER_FILE).read_bytes())
            row = dict(run_mod.walk_row(e, ledger), walk=e["walk"], slot=e["walk"])
            firsts.setdefault((row["task"], row["agent"]["harness"]), row)
        self.assertEqual(len({t for t, _ in firsts}), len(list((HERE / "tasks").glob("*.json"))),
                         "D2-design: a task has no registered walk to build its view from")
        for row in firsts.values():
            window(lambda: wr.production_design(row, "/tmp/pf1/" + drive.neutral_name(
                ct.walk_session_id(row["walk"]))))
        for walk in WALKS:
            entry = [e for e in reg["walks"] if e["walk"] == walk][0]
            with tempfile.TemporaryDirectory() as tmp:
                state["tmp"] = str(Path(tmp).resolve())
                base = Path(tmp) / walk
                wr.materialize_walk(root, wr._walk_rel(prefix, walk), base)
                ledger = json.loads((base / drive.LEDGER_FILE).read_bytes())
                row = dict(run_mod.walk_row(entry, ledger), walk=walk, slot=walk)
                take = types.SimpleNamespace(folder=str(base), cross_check=[])
                checker = drive.take_checker(design_for=lambda r, t: wr.production_design(r, "/tmp/pf1/" + (
                    drive.neutral_name(ct.walk_session_id(walk)))), records="walks")
                got = window(lambda: checker(row, take, []))
                self.assertTrue(got["checker_reasons"], f"{walk}: the checker read nothing")
        in_repo = {(f, n) for f, n in ran if f.startswith(str(REPO) + "/") and f != me and (f, n) != builder}
        self.assertTrue(in_repo, "D2-run: no study code ran")
        self.assertEqual(sorted({f for f, _ in in_repo} - bound), [], "D2-run: code outside CHECKER_CODE_FILES ran")
        files = {f for f in opened if f.startswith(str(REPO) + "/") and not f.endswith(".pyc")}
        self.assertIn(draft, files, "D2-design: the pre-registration was not read inside the window")
        self.assertEqual(sorted(files - bound - {draft}), [],
                         "D2-run: a study file outside CHECKER_CODE_FILES was opened")

    def test_d3_each_entry_is_gits_blob_id(self):
        manifest = ct.checker_code_manifest(REPO)
        got = subprocess.run(["git", "-C", str(REPO), "hash-object", "--no-filters", "--", *manifest],
                             capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(got, list(manifest.values()))
        tree = CodeTree(ct)
        try:
            g = ["git", "-C", str(tree.root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false"]
            subprocess.run(g[:3] + ["init", "-q"], check=True)
            subprocess.run(g + ["add", "--", *manifest], check=True)
            subprocess.run(g + ["commit", "-q", "-m", "t"], check=True)
            listed = subprocess.run(g + ["ls-tree", "-r", "HEAD", "--", *manifest], capture_output=True, text=True,
                                    check=True).stdout.splitlines()
            self.assertEqual({ln.split("\t")[1]: ln.split()[2] for ln in listed}, ct.checker_code_manifest(tree.root))
        finally:
            tree.close()

    def test_d4_d5_d6_standing(self):
        self.assertEqual(standing_cases(), [])

    def test_d7_shape(self):
        self.assertEqual(shape_problems(), [])

    def test_d10_writers_record_the_digest_in_force(self):
        self.assertEqual(writer_problems(), [])

    def test_d11_the_cache_reads_each_files_signature(self):
        self.assertEqual(cache_problems(), [])

    def test_d8_the_regrade_reads_no_digest(self):
        self.assertEqual(regrade_problems(), [])

    def test_d9_witnesses(self):
        for name, old, new, case in CT_MUTANTS:
            with self.subTest(witness=name):
                m = mutant(ct, old, new)
                try:
                    got = {"standing": lambda: standing_cases(m), "pin": lambda: pin_problems(m),
                           "shape": lambda: shape_problems(m), "writers": lambda: writer_problems(m),
                           "cache": lambda: cache_problems(m)}[case]()
                except Exception as e:  # noqa: BLE001 - a mutant that crashes its case is red too
                    got = [f"raised {type(e).__name__}: {e}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} {got[:1]}", end=" ", file=sys.stderr)
                self.assertTrue(got, name)
        import walk_regrade
        for name, old, new in WR_MUTANTS:
            with self.subTest(witness=name):
                try:
                    got = regrade_problems(mutant(walk_regrade, old, new), first=True)
                except Exception as e:  # noqa: BLE001
                    got = [f"raised {type(e).__name__}: {e}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} {got[:1]}", end=" ", file=sys.stderr)
                self.assertTrue(got, name)
        import run_checks
        for name, old, new in RC_MUTANTS:
            with self.subTest(witness=name):
                try:
                    got = run_checks_problems(mutant(run_checks, old, new))
                except Exception as e:  # noqa: BLE001
                    got = [f"raised {type(e).__name__}: {e}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} {got[:1]}", end=" ", file=sys.stderr)
                self.assertTrue(got, name)

    def test_d12_only_the_battery_gets_the_long_timeout(self):
        self.assertEqual(run_checks_problems(), [])

    def test_d13_the_messages_name_constants_or_code(self):
        """Review c99f114 MINOR 2: a stale walk reads "checker constants or code", and a recheck whose design view has
        no digest names a missing checker code file as a cause."""
        base = world("0" * 64)
        try:
            self.assertEqual(pw.checker_standing(base, "w-digest"),
                             "stale: checked under other checker constants or code; regrade it")
        finally:
            shutil.rmtree(base.parent, ignore_errors=True)
        for src in ((HERE / "pending_walk.py").read_text(), (HERE / "walk_regrade.py").read_text()):
            self.assertNotIn("checked under other checker constants;", src)
        self.assertIn('RegradeRefused("the design view\'s constants or code have no digest (PENDING, incomplete, or a "\n'
                      '                                     "checker code file missing)")',
                      (HERE / "walk_regrade.py").read_text())


if __name__ == "__main__":
    unittest.main()
