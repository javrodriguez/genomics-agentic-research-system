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
              empty); neither carries the other's name, and a claude-code checkout carries neither. Round 10 ruling 3:
              every CLAUDE.md of the checkout gets the copy, so gars/ carries the same native file with gars/CLAUDE.md's
              bytes, in the same one commit, and an origin already carrying gars/AGENTS.md refuses. An origin with no
              root CLAUDE.md, or one whose commit already carries the native name, refuses and leaves nothing.
              walk_builders.prepare hands build_run_tree the row's harness.
  R6-witness  walk_builders.py and box/take_config.py compiled in memory with the copy skipped, its bytes altered,
              the other CLI's name placed, the commit not amended, a fallback name configured, and (round 10
              ruling 3) the nested copies skipped: each goes red.

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

Ruling 2: the plan's fail-closed rule lands now. Until the record exists every codex and gemini walk refuses before
launch by name, and none runs with a shorter list; Claude Code walks are untouched.

  AE-closed   with no record, lease_secrets refuses at take start naming the record before any lease token is read,
              CodexLeaseRoad refuses when the walk is built, login_secrets refuses a Gemini take when its secrets()
              is made (not at the first scan), and walk_driver_for refuses a codex and a gemini row before
              drive.walk_driver is called; a Claude Code take's login_secrets, with no record and no WALK_LOGIN_FILES,
              is admitted and reads only its token; with a TEST DATA record each vendor road is admitted. Three
              witnesses (each road's record read deleted) go red.

Ruling 4: a codex or gemini take's secrets() carries ("email", the operator's address) and ("email", the take's
account address) after its tokens, read from the record at each scan (plan section 1a, account-email).

  AE-pairs    lease_secrets' and a Gemini login_secrets' secrets() on a TEST DATA record end with exactly the two
              email pairs, read again at each call (a rewritten record is the next scan's); a Claude Code take's
              carries none.
  AE-scan     a vendor take folder (tests/vendor_check_fixtures.py) whose turn-1 reply names the take's account
              address, scanned by box/scan_record.scan with that take's real secrets(): the address is masked with the
              email marker in every file it was in and gone from every byte, and check_take.vendor_email_problems
              counts 1; with the operator's address in turn 1 and the account's in turn 2, the hits sit in at least
              two files and still count 1, never above the scan's masked email hits (drive.py's bound).
  AE-pairs-witness  walk_builders.py compiled in memory with the operator's pair or the account's pair dropped from
              the secrets goes red on AE-scan.

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
NESTED_TEXT = "# Synthetic workspace instructions\n"
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
        (repo / "gars" / "CLAUDE.md").write_text(NESTED_TEXT)
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
            # round 10 ruling 3: every CLAUDE.md of the checkout, gars/CLAUDE.md included, gets the copy beside it
            nested = (tree / "gars" / "CLAUDE.md").read_bytes()
            for name in NATIVE.values():
                present = (tree / "gars" / name).exists()
                if present != (name == want):
                    out.append(f"{harness}: gars/ {'carries' if present else 'lacks'} {name}")
            if want and (tree / "gars" / want).is_file():
                placed = (tree / "gars" / want).read_bytes()
                if placed != nested or hashlib.sha256(placed).digest() != hashlib.sha256(NESTED_TEXT.encode()).digest():
                    out.append(f"{harness}: gars/{want} is not gars/CLAUDE.md's bytes")
                if tbi.git_bytes(tree, "show", f"HEAD:gars/{want}") != placed:
                    out.append(f"{harness}: gars/{want} is not in the checkout's one commit")
    for label, kw in (("an origin with no root CLAUDE.md", {"claude_md": None}),
                      ("an origin already carrying AGENTS.md", {"extra": {"AGENTS.md": "# other\n"}}),
                      ("an origin already carrying gars/AGENTS.md", {"extra": {"gars/AGENTS.md": "# other\n"}})):
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
    with mock.patch.object(tc, "CODEX_REASONING_EFFORT", {"gpt-6.1-sol": "medium"}), \
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
    want = {"claude-code": ["CLAUDE.md"], "codex": ["AGENTS.md"], "gemini": ["GEMINI.md"]}   # m15 (pf1-l4a)
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
    """fn(*args)'s BuilderRefused message, or None when it was admitted (any other exception is named, so a reader
    that crashes reads as a wrong refusal, never as a pass)."""
    try:
        fn(*args)
    except wb_mod.BuilderRefused as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return f"not a BuilderRefused: {type(e).__name__}"
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


def closed_problems(wb_mod, tmp: Path) -> list:
    """AE-closed on one walk_builders module (the real one or a witness): [] or each failure."""
    from box import scan_record
    out = []
    absent = str(tmp / "absent" / "account-emails.json")
    src = str(twb.lease_file(tmp))
    gemini_login = str(twb.login_file(f"GEMINI_API_KEY={twb.GEMINI_KEY}\n"))
    claude_login = str(twb.login_file("CLAUDE_CODE_OAUTH_TOKEN=" + "synthetic-claude-token-" + "a" * 12 + "\n"))
    reads = []
    real_lease, real_login = scan_record.read_lease_tokens, scan_record.read_login

    def counted(fn):
        return lambda *a, **k: reads.append(fn.__name__) or fn(*a, **k)

    def refuses(label, fn, *args):
        why = refusal(wb_mod, fn, *args)
        if why is None:
            out.append(f"AE-closed: {label} was admitted with no account record")
        elif "account-emails.json" not in why:
            out.append(f"AE-closed: {label} refused for another reason: {why}")

    with mock.patch.object(scan_record, "read_lease_tokens", counted(real_lease)), \
            mock.patch.object(scan_record, "read_login", counted(real_login)):
        with mock.patch.object(wb_mod, "account_emails_path", lambda: absent):
            refuses("lease_secrets", wb_mod.lease_secrets, src)
            if "read_lease_tokens" in reads:
                out.append("AE-closed: lease_secrets read the lease's tokens before refusing")
            refuses("CodexLeaseRoad", wb_mod.CodexLeaseRoad, src)
            refuses("login_secrets for a gemini take", wb_mod.login_secrets, gemini_login, "gemini")
            for row in ({"walk": "w-0001", "arm": "O", "agent": {"harness": "codex", "version": "0.162.1"}},
                        {"walk": "w-0001", "arm": "G", "agent": {"harness": "gemini", "version": "0.64.0"}}):
                built = []
                login = "-" if row["arm"] == "O" else gemini_login
                with walk_driver_world(wb_mod, tmp, built):
                    refuses(f"walk_driver_for a {row['agent']['harness']} row", wb_mod.walk_driver_for,
                            dict(WORLD, lease_path=src), row, login, tmp / "tree")
                if built:
                    out.append(f"AE-closed: a {row['agent']['harness']} row reached {built} with no account record")
        with mock.patch.object(wb_mod, "account_emails_path", side_effect=AssertionError("account_emails_path")), \
                mock.patch.object(twb.rt, "WALK_LOGIN_FILES", None, create=True):
            try:
                secrets = wb_mod.login_secrets(claude_login, "claude-code")
                if [k for k, _ in secrets()] != ["token"]:
                    out.append(f"AE-closed: a Claude Code take's secrets are {[k for k, _ in secrets()]}")
            except Exception as e:  # noqa: BLE001
                out.append(f"AE-closed: a Claude Code take was refused: {type(e).__name__}")
        reads.clear()
        with twb.account_boundary(wb_mod):
            for label, fn, args in (("lease_secrets", wb_mod.lease_secrets, (src,)),
                                    ("CodexLeaseRoad", wb_mod.CodexLeaseRoad, (src,)),
                                    ("login_secrets for a gemini take", wb_mod.login_secrets,
                                     (gemini_login, "gemini"))):
                why = refusal(wb_mod, fn, *args)
                if why is not None:
                    out.append(f"AE-closed: {label} refused on a TEST DATA record: {why}")
            if "read_login" in reads:
                out.append("AE-closed: the Gemini key was read before a scan asked")
    return out


# walk_driver_for's collaborators, faked at the boundary (test_walk_builders' B13 and B14 shape)
WORLD = {"rules_scanner": lambda paths: [], "runtime": "rt", "config_parent": "/synthetic", "budgets": (600, 5, 1),
         "take_spec": lambda r, c, t: "spec", "sidecar_for": None, "proxy": None, "lock_path": None, "hosts": None,
         "cgroup_dir_for": lambda t: "", "pin_for": None, "design_for": None, "uid_map": None, "clock": None,
         "sleep": None, "ownership": None, "settings_guard": None, "machine_gate": None}


@contextlib.contextmanager
def walk_driver_world(wb_mod, tmp: Path, built: list):
    drive = twb.MODS["drive"]
    with mock.patch.object(drive, "walk_driver", lambda **kw: built.append("drive.walk_driver") or "driver"), \
            mock.patch.object(drive, "WalkRepo", lambda **kw: built.append("drive.WalkRepo") or "repo"), \
            mock.patch.object(drive, "records_repo", lambda root: "/synthetic/repo"), \
            mock.patch.object(wb_mod, "build_walk_fixture", lambda r, t, p: ({"sha256": "0" * 64}, "/synthetic/src")), \
            mock.patch.object(wb_mod, "walk_identity", lambda *a, **k: {"walk": "w-0001"}), \
            mock.patch.object(twb.rt, "CODEX_SUBSCRIPTION_READY", True, create=True):
        yield


def pairs_problems(wb_mod, tmp: Path) -> list:
    """AE-pairs on one walk_builders module: [] or each failure."""
    out = []
    src = str(twb.lease_file(tmp))
    gemini_login = str(twb.login_file(f"GEMINI_API_KEY={twb.GEMINI_KEY}\n"))
    claude_login = str(twb.login_file("CLAUDE_CODE_OAUTH_TOKEN=" + "synthetic-claude-token-" + "a" * 12 + "\n"))
    with twb.account_boundary(wb_mod) as f:
        roads = {"codex": (wb_mod.lease_secrets(src), [("token", twb.ACCESS), ("token", twb.REFRESH)], CODEX_ACCOUNT),
                 "gemini": (wb_mod.login_secrets(gemini_login, "gemini"), [("token", twb.GEMINI_KEY)],
                            GEMINI_ACCOUNT)}
        for harness, (secrets, tokens, account) in roads.items():
            want = tokens + [("email", OPERATOR), ("email", account)]
            if secrets() != want:
                out.append(f"AE-pairs: a {harness} take's secrets() are not its tokens and the two addresses")
        os.chmod(f, 0o600)
        f.write_text(json.dumps(dict(RECORD, operator="operator-two@example.invalid")))
        for harness, (secrets, tokens, account) in roads.items():
            if secrets()[-2:] != [("email", "operator-two@example.invalid"), ("email", account)]:
                out.append(f"AE-pairs: a {harness} take's secrets() did not read the record again at the scan")
        if [k for k, _ in wb_mod.login_secrets(claude_login, "claude-code")()] != ["token"]:
            out.append("AE-pairs: a Claude Code take's secrets() carry more than its token")
    return out


def scan_problems(wb_mod, tmp: Path) -> list:
    """AE-scan on one walk_builders module: [] or each failure."""
    import check_take
    import scrub
    import vendor_check_fixtures as vcf
    from box import scan_record
    out = []
    src = str(twb.lease_file(tmp))
    gemini_login = str(twb.login_file(f"GEMINI_API_KEY={twb.GEMINI_KEY}\n"))
    with twb.account_boundary(wb_mod):
        for harness, account in (("codex", CODEX_ACCOUNT), ("gemini", GEMINI_ACCOUNT)):
            secrets = (wb_mod.lease_secrets(src) if harness == "codex"
                       else wb_mod.login_secrets(gemini_login, "gemini"))
            for label, replies, files_with in (
                    ("the account's address in one stream", [f"Synthetic reply naming {account}.", "Done."], 1),
                    ("two addresses in two turns", [f"Synthetic reply naming {OPERATOR}.",
                                                    f"Synthetic reply naming {account}."], 2)):
                parts = (vcf.codex_parts if harness == "codex" else vcf.gemini_parts)(replies=replies)
                folder = Path(tempfile.mkdtemp(dir=tmp))
                path = vcf.write(folder, harness, parts)
                kinds = {"transcript.jsonl": "transcript", "driver-ledger.json": "ledger"}
                files = [(str(p), "session" if p.parent.name == "session" else
                          "stream" if p.name.startswith("turn-") and p.suffix == ".jsonl" else kinds.get(p.name))
                         for p in sorted(folder.rglob("*")) if p.is_file()]
                files = [(p, k) for p, k in files if k]
                try:
                    result = scan_record.scan(files, secrets(), rules_scanner=lambda paths: [])
                except Exception as e:  # noqa: BLE001
                    out.append(f"AE-scan: {harness}, {label}: the scan raised {type(e).__name__}")
                    continue
                emails = [m for m in result["masked"] if m["kind"] == "email"]
                hit_files = {m["path"] for m in emails}
                if result["refused"] or len(hit_files) < files_with:
                    out.append(f"AE-scan: {harness}, {label}: {len(emails)} masked email hits in {len(hit_files)} "
                               f"files, {len(result['refused'])} refused")
                for p in folder.rglob("*"):
                    if p.is_file() and any(a.encode() in p.read_bytes() for a in (OPERATOR, account)):
                        out.append(f"AE-scan: {harness}, {label}: an address survived in {p.name}")
                if not any(scrub.NOTE.encode() in Path(p).read_bytes() for p in hit_files):
                    out.append(f"AE-scan: {harness}, {label}: no file carries the email marker")
                counted = check_take.vendor_email_problems(path)
                if len(counted) != 1 or len(counted) > len(emails):
                    out.append(f"AE-scan: {harness}, {label}: vendor_email_problems counts {len(counted)} over "
                               f"{len(emails)} masked hits")
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
    "the nested copies skipped (round 10 ruling 3)": (
        '    sources = sorted(p for p in listed if p == "CLAUDE.md" or p.endswith("/CLAUDE.md"))\n',
        '    sources = ["CLAUDE.md"]\n'),
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


class AEClosed(twb.Drafted):
    def test_ae_every_vendor_take_refuses_without_the_record(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(closed_problems(twb.wb(), Path(t)), [])

    def test_ae_witness_each_road_without_its_record_read_goes_red(self):
        for name, site in AE_CLOSED_WITNESSES.items():
            with self.subTest(witness=name), tempfile.TemporaryDirectory() as t:
                mod = compiled(HERE / "walk_builders.py", "walk_builders_ae_witness",
                               ((site, site.replace("account_emails(", "(lambda harness: None)(", 1)),))
                self.assertNotEqual(closed_problems(mod, Path(t)), [], f"witness {name} stayed green")


AE_CLOSED_WITNESSES = {
    "lease_secrets reads no record": ("    account_emails(rt.CODEX)                   "
                                      "# round 10 ruling 2: no record, no take\n"),
    "CodexLeaseRoad reads no record": ("        account_emails(rt.CODEX)                "
                                       "# round 10 ruling 2: no record, no walk\n"),
    "login_secrets reads no record": "        account_emails(rt.GEMINI)\n",
}


class AEPairs(twb.Drafted):
    def test_ae_a_vendor_takes_secrets_carry_both_addresses(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(pairs_problems(twb.wb(), Path(t)), [])

    def test_ae_a_swept_address_is_masked_and_counts_once(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(scan_problems(twb.wb(), Path(t)), [])

    def test_ae_witness_a_secrets_without_either_address_goes_red(self):
        for name, new in AE_PAIRS_WITNESSES.items():
            with self.subTest(witness=name), tempfile.TemporaryDirectory() as t:
                mod = compiled(HERE / "walk_builders.py", "walk_builders_ae_witness", ((PAIRS_SITE, new),))
                self.assertNotEqual(scan_problems(mod, Path(t)), [], f"witness {name} stayed green")


PAIRS_SITE = '    return [("email", operator), ("email", account)]\n'
AE_PAIRS_WITNESSES = {
    "the operator's pair dropped": '    return [("email", account)]\n',
    "the account's pair dropped": '    return [("email", operator)]\n',
}


class AERecord(twb.Drafted):
    def test_ae_the_account_record_is_read_and_refused_by_name(self):
        self.assertEqual(record_problems(twb.wb()), [])


AE_WITNESSES = {
    "the extra-key check deleted": "    if extra:\n",
    "the address check deleted": "        if not _is_address(value):\n",
    "the missing-key check deleted": "        if key not in doc:\n",
    "the mode check deleted": ("    if stat.S_IMODE(rec.st_mode) != 0o600:\n"
                               "        raise BuilderRefused(f\"{where}: the account record"),
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
