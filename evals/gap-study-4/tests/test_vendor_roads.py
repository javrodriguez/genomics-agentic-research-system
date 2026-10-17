#!/usr/bin/env python3
"""Lane vendor-admission T4 P2: R-6's road for the vendor arms' instruction files (glitch-b5's ruling R-6 of Sat 17 Oct
2026, about 12:35 EDT, under Javier's delegation: every arm gets byte-identical instructions under its CLI's native
name, AGENTS.md for Codex and GEMINI.md for Gemini, bytes equal to the pinned tree's CLAUDE.md, each bound by sha256 to
it; no configured fallback names used or accepted; where the harness has no road to place those files in a vendor
take's checkout, P2 writes it with its own red test; lane-reports/vendor-T4-PLAN.md v4 section 11).

  R6-config   box/take_config.INSTRUCTION_FILES names each vendor CLI's native file (AGENTS.md, GEMINI.md); neither
              the codex config.toml nor the gemini settings.json configures an instruction-file name (no
              project_doc_fallback_filenames, no context.fileName, nor any value naming CLAUDE.md); the draft's
              instruction_files are the native names (build_draft).
  R6-road     walk_builders.build_run_tree(..., harness=) on a scratch origin whose commit carries CLAUDE.md: a codex
              checkout carries AGENTS.md and a gemini one GEMINI.md, each byte-identical to the commit's CLAUDE.md
              (sha256 equal), in the checkout's one commit (its neutral subject, a clean status, run_tree_problems
              empty); neither carries the other's name, and a claude-code checkout carries neither. An origin with no
              root CLAUDE.md, or one whose commit already carries the native name, refuses and leaves nothing.
              walk_builders.prepare hands build_run_tree the row's harness.
  R6-witness  walk_builders.py and box/take_config.py compiled in memory with the copy skipped, its bytes altered,
              the other CLI's name placed, the commit not amended, and a fallback name configured: each goes red.

Round 10 (glitch-b5, Sat 17 Oct 2026, confirmed to the cloud session the same day), ruling 1: the account record
is account-emails.json in the private folder that holds run_take.WALK_LOGIN_FILES' account folders, outside every
repository, mode 600: a JSON object with exactly the keys "operator", "codex" and "gemini", each value an email
address, read by name at scan time; the reader and its refusals live in walk_builders.

  AE-record   walk_builders.account_emails_path names that file (WALK_LOGIN_FILES absent, or its account folders
              under two parents, refuses by name); account_emails(harness) on a TEST DATA record reads the operator's
              address and the harness's account address, in that order; a missing file, a missing key for the take's
              harness (the other vendor's key may be absent), an extra key, a value that is not an address, a file
              that is not a JSON object, a mode other than 600, a link, a file inside a repository, and a harness
              that is neither codex nor gemini each refuse by name, and no refusal carries an address.
  AE-witness  walk_builders.py compiled in memory with each of the extra-key, address, missing-key and mode checks
              deleted goes red.

Scratch repositories and fakes only, under test_walk_builders' module setup: no take, model, vendor, network,
Docker, credential or holdout. Every address here is TEST DATA under the reserved .invalid domain.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import tempfile
import tomllib
import types
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
HERE = TESTS.parent
for p in (str(HERE), str(TESTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

import test_walk_builders as twb  # noqa: E402

tbi = twb.tbi
PINNED_TEXT = "# Synthetic instructions\n\nRead the project's README first.\n"
NATIVE = {"codex": "AGENTS.md", "gemini": "GEMINI.md"}


def setUpModule():
    twb.setUpModule()


def tearDownModule():
    twb.tearDownModule()


@contextlib.contextmanager
def origin(claude_md=PINNED_TEXT, extra=None):
    """A scratch origin: one commit holding CLAUDE.md (unless None), gars/CLAUDE.md, src/ and evals/."""
    with tbi.scratch_repo() as repo:
        (repo / "src").mkdir()
        (repo / "src" / "a.txt").write_text("synthetic source\n")
        (repo / "gars").mkdir()
        (repo / "gars" / "CLAUDE.md").write_text("# Synthetic workspace instructions\n")
        (repo / "evals").mkdir()
        (repo / "evals" / "hidden.txt").write_text("synthetic study file\n")
        if claude_md is not None:
            (repo / "CLAUDE.md").write_text(claude_md)
        for rel, text in (extra or {}).items():
            (repo / rel).write_text(text)
        tbi.git(repo, "add", "-A")
        tbi.git(repo, "commit", "-q", "-m", "A synthetic origin")
        yield repo, tbi.git(repo, "rev-parse", "HEAD")


def road_problems(wb_mod) -> list:
    """R6-road on one walk_builders module (the real one or a witness): [] or each failure."""
    out = []
    drive = twb.MODS["drive"]
    for harness in ("codex", "gemini", "claude-code"):
        with origin() as (repo, sha), twb.temp_root():
            try:
                tree = Path(wb_mod.build_run_tree("w-0001", repo=repo, commit=sha, exclude=["evals"],
                                                  harness=harness))
            except Exception as e:  # noqa: BLE001
                out.append(f"{harness}: build_run_tree raised {type(e).__name__}: {e}")
                continue
            pinned = (tree / "CLAUDE.md").read_bytes()
            want = NATIVE.get(harness)
            for name in NATIVE.values():
                present = (tree / name).exists()
                if present != (name == want):
                    out.append(f"{harness}: the checkout {'carries' if present else 'lacks'} {name}")
            if want and (tree / want).is_file():
                placed = (tree / want).read_bytes()
                committed = tbi.git_bytes(tree, "show", f"HEAD:{want}") if hasattr(tbi, "git_bytes") else None
                if hashlib.sha256(placed).hexdigest() != hashlib.sha256(PINNED_TEXT.encode()).hexdigest() \
                        or placed != pinned:
                    out.append(f"{harness}: {want} is not the pinned CLAUDE.md's bytes")
                if committed is not None and committed != placed:
                    out.append(f"{harness}: {want} is not in the checkout's one commit")
            if tbi.git(tree, "rev-list", "--all", "--count") != "1" \
                    or tbi.git(tree, "log", "-1", "--format=%s") != drive.TREE_SUBJECT \
                    or tbi.git(tree, "status", "--porcelain") != "":
                out.append(f"{harness}: the checkout is not one commit, its neutral subject and a clean status")
            if drive.run_tree_problems(tree, twb.walk_sid("w-0001"), ["evals"]):
                out.append(f"{harness}: run_tree_problems on the built checkout")
    for label, kw in (("an origin with no root CLAUDE.md", {"claude_md": None}),
                      ("an origin already carrying AGENTS.md", {"extra": {"AGENTS.md": "# other\n"}})):
        with origin(**kw) as (repo, sha), twb.temp_root() as tmp:
            try:
                wb_mod.build_run_tree("w-0001", repo=repo, commit=sha, exclude=["evals"], harness="codex")
                out.append(f"{label}: built a codex checkout")
            except wb_mod.BuilderRefused:
                pass
            except Exception as e:  # noqa: BLE001
                out.append(f"{label}: raised {type(e).__name__}: {e}")
            if list(Path(tmp).iterdir()):
                out.append(f"{label}: a refused build left its checkout")
    return out


def config_problems(tc) -> list:
    """R6-config on one take_config module: [] or each failure."""
    out = []
    if getattr(tc, "INSTRUCTION_FILES", None) != {tc.CODEX: "AGENTS.md", tc.GEMINI: "GEMINI.md"}:
        out.append(f"INSTRUCTION_FILES is {getattr(tc, 'INSTRUCTION_FILES', None)!r}")
    with mock.patch.object(tc, "CODEX_REASONING_EFFORT", "medium"), \
            mock.patch.object(tc, "GEMINI_THINKING", {"path": "model.thinkingLevel", "value": "default"}), \
            mock.patch.object(tc, "GEMINI_AUTH_SETTING", {"path": "security.auth.selectedType", "value": "x"}):
        codex = tomllib.loads(tc.files_for(tc.CODEX, model="gpt-6.1-sol")[tc.CODEX_CONFIG].decode())
        gemini = json.loads(tc.files_for(tc.GEMINI, model="gemini-3.8-flash")[tc.GEMINI_SETTINGS_PATH].decode())
    if "project_doc_fallback_filenames" in codex or "CLAUDE.md" in json.dumps(codex):
        out.append(f"the codex config names an instruction file: {codex}")
    if "fileName" in json.dumps(gemini.get("context", {})) or "CLAUDE.md" in json.dumps(gemini):
        out.append(f"the gemini settings name an instruction file: {gemini}")
    return out


def draft_problems() -> list:
    """The committed draft's instruction_files (build_draft --check binds the draft to the writer, and
    test_build_draft's R15.instructions binds the writer to take_config.INSTRUCTION_FILES)."""
    got = json.loads((HERE / "prereg-draft.json").read_text())["instruction_files"]
    want = {"codex": ["AGENTS.md"], "gemini": ["GEMINI.md"]}
    return [] if got == want else [f"the draft's instruction_files are {got}"]


def compiled(path: Path, name: str, edits=()) -> types.ModuleType:
    """A module compiled in memory from `path` with `edits` applied (each old text occurring exactly once)."""
    src = path.read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"mutation site occurs {src.count(old)} times in {path.name}: {old!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    mod.__package__ = "box" if path.parent.name == "box" else ""
    sys.modules[name] = mod
    try:
        exec(compile(src, str(path) + " (witness)", "exec"), mod.__dict__)  # noqa: S102
    finally:
        sys.modules.pop(name, None)
    return mod


# ------------------------------------------------------------------------------------------- the account record
# TEST DATA only: clearly fake addresses under the reserved .invalid domain, never a real account's.
OPERATOR = "operator@example.invalid"
CODEX_ACCOUNT = "codex-account@example.invalid"
GEMINI_ACCOUNT = "gemini-account@example.invalid"
RECORD = {"operator": OPERATOR, "codex": CODEX_ACCOUNT, "gemini": GEMINI_ACCOUNT}
ADDRESSES = (OPERATOR, CODEX_ACCOUNT, GEMINI_ACCOUNT)


@contextlib.contextmanager
def account_folder(record=RECORD, *, raw=None, mode=0o600):
    """A private folder laid out as the box's: one folder per run_take.WALK_LOGIN_FILES account (patched to it), and
    account-emails.json beside them holding `record` as JSON (or `raw` text; neither: no file). Yields the file."""
    with tempfile.TemporaryDirectory() as t:
        top = Path(t) / "secrets"
        top.mkdir(mode=0o700)
        files = {}
        for account in ("claude1", "r4-g"):
            (top / account).mkdir(mode=0o700)
            files[account] = str(top / account / "login")
        f = top / "account-emails.json"
        if record is not None or raw is not None:
            f.write_text(raw if raw is not None else json.dumps(record))
            os.chmod(f, mode)
        with mock.patch.object(twb.rt, "WALK_LOGIN_FILES", files, create=True):
            yield f


def refusal(wb_mod, fn, *args) -> str | None:
    """fn(*args)'s BuilderRefused message, or None when it was admitted."""
    try:
        fn(*args)
    except wb_mod.BuilderRefused as e:
        return str(e)
    return None


def record_problems(wb_mod) -> list:
    """AE-record on one walk_builders module (the real one or a witness): [] or each failure."""
    out = []
    if not callable(getattr(wb_mod, "account_emails", None)) or not callable(
            getattr(wb_mod, "account_emails_path", None)):
        return ["AE-record: walk_builders has no account_emails reader (round 10 ruling 1)"]
    said = []

    def refused(label, fn, *args, naming=()):
        why = refusal(wb_mod, fn, *args)
        if why is None:
            out.append(f"AE-record: {label} was admitted")
            return
        said.append(why)
        for name in ("account-emails.json",) + tuple(naming):
            if name not in why:
                out.append(f"AE-record: {label} refused without naming {name}: {why}")

    with account_folder() as f:
        if wb_mod.account_emails_path() != str(f):
            out.append(f"AE-record: the record's path is {wb_mod.account_emails_path()!r}, not {str(f)!r}")
        for harness, want in (("codex", (OPERATOR, CODEX_ACCOUNT)), ("gemini", (OPERATOR, GEMINI_ACCOUNT))):
            try:
                got = tuple(wb_mod.account_emails(harness))
            except wb_mod.BuilderRefused as e:
                out.append(f"AE-record: a complete record refused {harness}: {e}")
                continue
            if got != want:
                out.append(f"AE-record: {harness} read {got!r}, not the operator's and its account's addresses")
        for harness in ("claude-code", "synthetic-harness"):
            refused(f"a {harness} take", wb_mod.account_emails, harness, naming=(harness,))
        os.chmod(f, 0o644)
        refused("a record of mode 644", wb_mod.account_emails, "codex", naming=("600",))
        os.chmod(f, 0o600)
        link = f.parent / "account-emails-link.json"
        link.symlink_to(f)
        refused("a link to the record", wb_mod.account_emails, "codex", str(link), naming=("link",))
        (f.parent / ".git").mkdir()
        refused("a record inside a repository", wb_mod.account_emails, "codex", naming=("repository",))
    with mock.patch.object(twb.rt, "WALK_LOGIN_FILES", None, create=True):
        refused("a tree without WALK_LOGIN_FILES", wb_mod.account_emails_path, naming=("WALK_LOGIN_FILES",))
    with account_folder() as f:
        twb.rt.WALK_LOGIN_FILES["r4-g"] = str(f.parent.parent / "elsewhere" / "r4-g" / "login")
        refused("account folders under two parents", wb_mod.account_emails_path, naming=("WALK_LOGIN_FILES",))
    with account_folder(None):
        for harness in ("codex", "gemini"):
            refused(f"no record ({harness})", wb_mod.account_emails, harness)
    with account_folder({"operator": OPERATOR, "codex": CODEX_ACCOUNT}):
        if refusal(wb_mod, wb_mod.account_emails, "codex") is not None:
            out.append("AE-record: a codex take refused for the gemini key's absence")
        refused("a gemini take with no gemini key", wb_mod.account_emails, "gemini", naming=('"gemini"',))
    with account_folder({"codex": CODEX_ACCOUNT, "gemini": GEMINI_ACCOUNT}):
        for harness in ("codex", "gemini"):
            refused(f"no operator key ({harness})", wb_mod.account_emails, harness, naming=('"operator"',))
    with account_folder(dict(RECORD, claude="claude-account@example.invalid")):
        for harness in ("codex", "gemini"):
            refused(f"an extra key ({harness})", wb_mod.account_emails, harness, naming=('"claude"',))
    for value in ("not-an-address", "two@example", "a b@example.invalid", "x@example.invalid\n", "@example.invalid",
                  "", 42, None, ["codex-account@example.invalid"]):
        with account_folder(dict(RECORD, codex=value)):
            refused(f"a codex value {value!r}", wb_mod.account_emails, "codex", naming=('"codex"',))
    for label, raw in (("a JSON list", json.dumps([RECORD])), ("text that is not JSON", "{operator"),
                       ("an empty file", "")):
        with account_folder(raw=raw):
            refused(label, wb_mod.account_emails, "codex")
    for why in said:
        if any(a in why for a in ADDRESSES + ("claude-account@example.invalid",)):
            out.append(f"AE-record: a refusal carries an address: {why}")
    return out


class R6Config(twb.Drafted):
    def test_r6_no_configured_fallback_name(self):
        from box import take_config
        self.assertEqual(config_problems(take_config), [])

    def test_r6_the_draft_names_the_native_files(self):
        self.assertEqual(draft_problems(), [])


class R6Road(twb.Drafted):
    def test_r6_each_vendor_checkout_carries_its_native_copy(self):
        self.assertEqual(road_problems(twb.wb()), [])

    def test_r6_prepare_hands_build_run_tree_the_rows_harness(self):
        mod = twb.wb()
        tmp = twb.scratch("r6")
        built = []
        args = types.SimpleNamespace(walk="w-0001", **twb.gemini_cell())
        good = str(twb.login_file(f"GEMINI_API_KEY={twb.GEMINI_KEY}\n"))
        base = {"agent_version": "0.64.0", "login_path": "/synthetic/never-read", "gemini_login_path": good,
                "run_tree_origin": ("/synthetic/repo", "0" * 40), "run_tree_exclude": ["evals"]}
        with mock.patch.object(mod, "build_run_tree", lambda *a, **k: built.append(k) or tmp / "tree"):
            mod.prepare(base, args)
        self.assertEqual([k.get("harness") for k in built], ["gemini"])


WB_WITNESSES = {
    "the copy skipped": ("    target.write_bytes(pinned)\n", "    pass\n"),
    "its bytes altered": ("    target.write_bytes(pinned)\n", "    target.write_bytes(pinned + b'x')\n"),
    "the other CLI's name": ('    name = take_config.INSTRUCTION_FILES.get(harness)\n',
                             '    name = {"codex": "GEMINI.md", "gemini": "AGENTS.md"}.get(harness)\n'),
    "the commit not amended": ('        ("commit", "-q", "--amend", "--no-verify", "--no-edit"),\n', ""),
}


class R6Witnesses(twb.Drafted):
    def test_r6_witness_each_road_mutant_goes_red(self):
        for name, edit in WB_WITNESSES.items():
            with self.subTest(witness=name):
                mod = compiled(HERE / "walk_builders.py", "walk_builders_r6_witness", (edit,))
                self.assertNotEqual(road_problems(mod), [], f"witness {name} stayed green")

    def test_r6_witness_a_fallback_name_configured_goes_red(self):
        from box import take_config
        for attr, value in (("CODEX_TOP", take_config.CODEX_TOP + (("project_doc_fallback_filenames", ["CLAUDE.md"]),)),
                            ("GEMINI_SETTINGS", take_config.GEMINI_SETTINGS + (("context.fileName", ["CLAUDE.md"]),))):
            with self.subTest(witness=attr), mock.patch.object(take_config, attr, value):
                self.assertNotEqual(config_problems(take_config), [], f"a fallback in {attr} stayed green")


class AERecord(twb.Drafted):
    def test_ae_the_account_record_is_read_and_refused_by_name(self):
        self.assertEqual(record_problems(twb.wb()), [])


AE_WITNESSES = {
    "the extra-key check deleted": "    if extra:\n",
    "the address check deleted": "        if not _is_address(value):\n",
    "the missing-key check deleted": "        if key not in doc:\n",
    "the mode check deleted": "    if stat.S_IMODE(st.st_mode) != 0o600:\n        raise BuilderRefused(f\"{path}: the account record",
}


class AEWitnesses(twb.Drafted):
    def test_ae_witness_each_record_mutant_goes_red(self):
        for name, site in AE_WITNESSES.items():
            with self.subTest(witness=name):
                new = site.replace("    if ", "    if False and ", 1)
                mod = compiled(HERE / "walk_builders.py", "walk_builders_ae_witness", ((site, new),))
                self.assertNotEqual(record_problems(mod), [], f"witness {name} stayed green")


if __name__ == "__main__":
    unittest.main()
