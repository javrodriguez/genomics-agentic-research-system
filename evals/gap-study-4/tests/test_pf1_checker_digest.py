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
  D8-regrade   the vendor regrade reads no checker digest: regrade_doc of committed pending walks w-o46 and w-g21 is
               byte-identical with the code tree edited and with checker_constants_sha256 raising.
  D9-witness   each mutant below turns its case red.
  D10-writers  what a checked walk records (the claude-code side's and the vendor side's digest, which walk_regrade's
               recheck also writes) is what coverage reads as in force, and both move with the code.
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
EXTRAS = (STUDY + "drive.py", STUDY + "vendor_provenance.py", STUDY + "routing.json")
# Function-level imports in bound modules (other than check_take.py) that leave the set: none of them runs while a
# walk is checked (D2 profiles it), so none is bound. A new one fails D1 until it is classified here or bound.
LAZY_OUTSIDE = {
    (STUDY + "batch.py", "costs"), (STUDY + "batch.py", "run_builders"),
    (STUDY + "box/run_take.py", "box.preflight"),
    (STUDY + "drive.py", "walk_register"), (STUDY + "drive.py", "box.ownership"),
    (STUDY + "drive.py", "box.settings_guard"), (STUDY + "drive.py", "fixtures.gen_explain_not_act"),
    (STUDY + "prereg.py", "freeze"), (STUDY + "prereg.py", "order_beacon"),
    (STUDY + "takes.py", "run"), (STUDY + "takes.py", "check_results"),
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


def rule_set(mod=None) -> set:
    start = REPO / STUDY / "check_take.py"
    seen, todo = set(), [(start, False)]
    while todo:
        path, top = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        todo += [(p, True) for n in _imports(path, module_level_only=top) for p in (_resolve(n),) if p]
    return {p.relative_to(REPO).as_posix() for p in seen} | set(EXTRAS) | fixture_readmes(mod or ct)


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
        with mock.patch.object(mod, "CHECKER_CODE_ROOT", tree.root), mock.patch.dict(sys.modules,
                                                                                    {"check_take": mod}):
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
    want = hashlib.sha256(json.dumps({"checker_code_sha256": code, "constants_sha256": consts}, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()
    with mock.patch.object(mod, "CHECKER_CODE_ROOT", REPO):
        if mod.checker_code_manifest() != lines:
            out.append("D7-shape: the manifest is not each file's git blob id")
        if mod.checker_code_sha256() != code:
            out.append("D7-shape: checker_code_sha256 is not the sha256 of the manifest")
        if mod.constants_only_sha256() != consts:
            out.append("D7-shape: constants_only_sha256 is not B5's constants-only digest")
        if mod.checker_constants_sha256() != want:
            out.append("D7-shape: checker_constants_sha256 is not the sha256 of its two halves")
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
    claude = mod.Design(task_id="t", spec={}, pre=dict(pre, leak_words=[]), harness="claude-code")
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


def regrade_bytes_under(wmod, walk: str, *, root=None, broken=False) -> bytes:
    patches = [mock.patch.object(ct, "CHECKER_CODE_ROOT", root or REPO)]
    if broken:
        def boom(*a, **k):
            raise AssertionError("the regrade read a checker digest")
        patches += [mock.patch.object(ct, "checker_constants_sha256", boom),
                    mock.patch.object(ct, "checker_code_sha256", boom)]
    for p in patches:
        p.start()
    try:
        return wmod.regrade_bytes(wmod.regrade_doc(walk, HERE))
    finally:
        for p in reversed(patches):
            p.stop()


def regrade_problems(wmod=None) -> list:
    """D8: each pending walk's regrade, the same bytes with the code tree edited and with the digests raising."""
    import walk_regrade
    wmod = wmod or walk_regrade
    out = []
    tree = CodeTree(ct)
    try:
        tree.edit(STUDY + "check_take.py", *CODE_EDIT, after=SESSION_STORE)
        for walk in PENDING_WALKS:
            try:
                plain = regrade_bytes_under(wmod, walk)
                edited = regrade_bytes_under(wmod, walk, root=tree.root)
                if plain != edited:
                    out.append(f"D8-regrade {walk}: the regrade moved with the checker's code")
                if regrade_bytes_under(wmod, walk, broken=True) != plain:
                    out.append(f"D8-regrade {walk}: the regrade differs with the digests raising")
            except AssertionError as e:
                out.append(f"D8-regrade {walk}: {e}")
    finally:
        tree.close()
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


CT_MUTANTS = (
    ("binding-dropped", "    return _bound_digest(constants_only_sha256(constants), checker_code_sha256())",
     "    return constants_only_sha256(constants)", "standing"),
    ("bytes-not-hashed", "        out[rel] = git_blob_id(p.read_bytes())", "        out[rel] = git_blob_id(rel.encode())",
     "standing"),
    ("file-dropped", '    "evals/gap-study-4/drive.py",\n', "", "pin"),
    ("missing-file-skipped", "            raise CheckRefused(f\"the checker's code file {rel} is missing or a link",
     "            continue\n            raise CheckRefused(f\"the checker's code file {rel} is missing or a link",
     "shape"),
    ("blob-header-dropped", '    return hashlib.sha1(b"blob %d\\0" % len(raw) + raw).hexdigest()',
     "    return hashlib.sha1(raw).hexdigest()", "shape"),
    ("claude-writer-constants-only",
     '        got["driver_constants"].pop("permission_mode_by_arm", None)\n        return checker_constants_sha256(got)\n'
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


class TheCheckerCodeDigest(unittest.TestCase):
    def test_d1_the_list_is_the_rule(self):
        self.assertEqual(pin_problems(ct), [])

    def test_d2_checking_runs_and_opens_listed_files_only(self):
        import batch
        import drive
        import routing
        import run as run_mod
        import walk_regrade as wr
        root, prefix = wr._repo(HERE)
        reg = json.loads((HERE / "rehearsals" / "register.json").read_text())
        bound = {str(REPO / rel) for rel in ct.CHECKER_CODE_FILES}
        me = str(Path(__file__).resolve())
        ran, opened = set(), set()
        state = {"on": False}

        def prof(frame, event, arg):
            if event == "call" and state["on"]:
                ran.add(frame.f_code.co_filename)

        def audit(event, args):
            if event == "open" and state["on"] and isinstance(args[0], (str, Path)):
                opened.add(str(Path(args[0]).resolve()) if not str(args[0]).startswith(tmp_root) else "")
        sys.addaudithook(audit)
        for walk in WALKS:
            entry = [e for e in reg["walks"] if e["walk"] == walk][0]
            with tempfile.TemporaryDirectory() as tmp:
                tmp_root = str(Path(tmp).resolve())
                base = Path(tmp) / walk
                wr.materialize_walk(root, wr._walk_rel(prefix, walk), base)
                ledger = json.loads((base / drive.LEDGER_FILE).read_bytes())
                row = dict(run_mod.walk_row(entry, ledger), walk=walk, slot=walk)
                design = ct.checker_view(ct.design_view(row, pin=batch.expected_pin(row, routing.load_table()),
                                                        run_tree="/tmp/pf1/" + drive.neutral_name(
                                                            ct.walk_session_id(walk))))
                take = types.SimpleNamespace(folder=str(base), cross_check=[])
                checker = drive.take_checker(design_for=lambda r, t: design, records="walks")
                state["on"] = True
                sys.setprofile(prof)
                try:
                    got = checker(row, take, [])
                finally:
                    sys.setprofile(None)
                    state["on"] = False
                self.assertTrue(got["checker_reasons"], f"{walk}: the checker read nothing")
        in_repo = {f for f in ran if f.startswith(str(REPO) + "/") and f != me}
        self.assertTrue(in_repo, "D2-run: no study code ran")
        self.assertEqual(sorted(in_repo - bound), [], "D2-run: code outside CHECKER_CODE_FILES ran")
        files = {f for f in opened if f.startswith(str(REPO) + "/") and not f.endswith(".pyc")}
        self.assertEqual(sorted(files - bound), [], "D2-run: a study file outside CHECKER_CODE_FILES was opened")

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

    def test_d8_the_regrade_reads_no_digest(self):
        self.assertEqual(regrade_problems(), [])

    def test_d9_witnesses(self):
        for name, old, new, case in CT_MUTANTS:
            with self.subTest(witness=name):
                m = mutant(ct, old, new)
                try:
                    got = {"standing": lambda: standing_cases(m), "pin": lambda: pin_problems(m),
                           "shape": lambda: shape_problems(m), "writers": lambda: writer_problems(m)}[case]()
                except Exception as e:  # noqa: BLE001 - a mutant that crashes its case is red too
                    got = [f"raised {type(e).__name__}: {e}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} {got[:1]}", end=" ", file=sys.stderr)
                self.assertTrue(got, name)
        import walk_regrade
        for name, old, new in WR_MUTANTS:
            with self.subTest(witness=name):
                try:
                    got = regrade_problems(mutant(walk_regrade, old, new))
                except Exception as e:  # noqa: BLE001
                    got = [f"raised {type(e).__name__}: {e}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} {got[:1]}", end=" ", file=sys.stderr)
                self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main()
