#!/usr/bin/env python3
"""The environment record: required of a graded take, read and never refused on a walk (decision 4).

    python3 evals/gap-study-2/test_harness.py TheEnvironmentRecordIsRequired

check_take.environment_problems() reads environment.json beside a transcript against the pre-registration's
`environment_record` block. These tests inject their own pre-registration (the shared contract's block and
the twelve stripped names), so they do not wait on the draft and do not change when it does.

The take they read is test-fixtures/environment-check/take/: a hand-built number-fidelity control take, valid
under every operator-side check, whose session id is uuid5(namespace, ROW_COMMIT). In process, the checker's
ledger is a stub holding that one row; end to end, a throwaway repository commits the row for real and the
take is re-bound to that commit's session id, so the command line reaches the environment check the way a
graded take does (structural lesson 12). A refusal is each test's own edit of a copy; the fixture itself is
only ever read.

No model, no network. stdlib only.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import scratch_git  # noqa: E402

FIX = HERE / "test-fixtures" / "environment-check"
TAKE = FIX / "take"
WALK = FIX / "walk"
# The take records the fixture checkout's stand-in instruction file, so an edit of the repository's own
# gars/CLAUDE.md never turns it red. The walk is a copy of the mutation battery's walk, which records the
# repository's file, and is read against the repository as that walk is.
FIXTURE_CHECKOUT = HERE / "test-fixtures" / "checkout"

ROW_COMMIT = "3c1e5b7a9d2f4608b1a3c5e7d9f1b3a5c7e9d1f3"
ROW = {"task": "number-fidelity", "half": "control", "model": "claude-opus-5", "take": 1}

# Decision 5 and J4: the twelve inherited session names, stripped by explicit name.
STRIPPED_ENV = ["CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION",
                "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_EXECPATH",
                "CLAUDE_AGENT_SDK_VERSION", "CLAUDE_EFFORT", "CLAUDE_PID", "CLAUDE_CODE_ENABLE_TASKS",
                "CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING"]

# The shared contract's draft block, as the builders code against it.
ENVIRONMENT_RECORD = {
    "file": "environment.json",
    "schema": 1,
    "name_patterns": {
        "harness": ["^ANTHROPIC_", "^CLAUDE_CODE_USE_(BEDROCK|VERTEX|FOUNDRY)$", "^CLAUDE_CODE_SKIP_.*_AUTH$",
                    "^CLAUDE_CODE_OAUTH_TOKEN$", "^CLAUDE_CODE_OAUTH_REFRESH_TOKEN$",
                    "^CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR$", "^CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR$",
                    "^CLAUDE_CODE_SESSION_ACCESS_TOKEN$", "^CLAUDE_CODE_API_BASE_URL$",
                    "^CLAUDE_CODE_CUSTOM_OAUTH_URL$", "^AWS_", "^GOOGLE_APPLICATION_CREDENTIALS$", "^AZURE_"],
        "generic": ["(API_?KEY|AUTH_?TOKEN|ACCESS_?TOKEN|_TOKEN$|SECRET|CREDENTIAL|PASSWORD)"],
    },
    "match": "re.search, case-sensitive; harness first",
    "api_key_variables": ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_FOUNDRY_API_KEY",
                          "ANTHROPIC_AWS_API_KEY", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR", "AWS_BEARER_TOKEN_BEDROCK"],
    "billing_route_variables": ["CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
                                "ANTHROPIC_BASE_URL", "CLAUDE_CODE_API_BASE_URL"],
    "subscription_token_variables": ["CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
                                     "CLAUDE_CODE_SESSION_ACCESS_TOKEN"],
    "credential_source_key": "system/init.apiKeySource",
    "subscription_source": None,
}

# Not a variable name: what a record would carry if a value were written where a name belongs.
PLANTED_VALUE = "placeholder value 0123"

# What the run tree must never be told: where takes land. The copy made for the command line leaves these out.
LIVE_NAMES = {"takes.json", "transcripts", "rehearsals", "pauses", "walks", "results", "analysis.json",
              "COSTS.md", "prereg.json", "verification", "__pycache__"}


def load_check_take(name: str = "gap_check_take_environment"):
    """This study's check_take, by path: the first study has a file of the same name."""
    spec = importlib.util.spec_from_file_location(name, HERE / "check_take.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def record_pre() -> dict:
    """The pre-registration in force, with the contract's environment block and the stripped names in it."""
    ct = load_check_take()
    pre = copy.deepcopy(ct.prereg.load())
    pre["environment_record"] = copy.deepcopy(ENVIRONMENT_RECORD)
    pre.setdefault("driver_constants", {})["stripped_env"] = list(STRIPPED_ENV)
    return pre


@contextlib.contextmanager
def injected(ct, pre: dict):
    saved = ct.prereg._cache
    ct.prereg._cache = pre
    try:
        yield pre
    finally:
        ct.prereg._cache = saved


def bound_checker():
    """check_take with its ledger holding the fixture's one row, and its pinned tree the fixture checkout."""
    ct = load_check_take()
    ct.REPO = FIXTURE_CHECKOUT
    ct.takes_mod = types.SimpleNamespace(load_rows=lambda: [dict(ROW)], row_commits=lambda: {0: ROW_COMMIT},
                                         session_id_for=ct.takes_mod.session_id_for)
    return ct


def write_record(folder: Path, rec, rebind: bool = True) -> bytes:
    body = rec if isinstance(rec, bytes) else (json.dumps(rec, indent=2) + "\n").encode("utf-8")
    (folder / "environment.json").write_bytes(body)
    if rebind:
        led = json.loads((folder / "driver-ledger.json").read_text())
        led["environment"] = {"file": "environment.json", "sha256": hashlib.sha256(body).hexdigest()}
        (folder / "driver-ledger.json").write_text(json.dumps(led, indent=2) + "\n")
    return body


def run_cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *argv], capture_output=True, text=True)


class TheEnvironmentRecordIsRequired(unittest.TestCase):
    """Decision 4: a graded take without a whole, bound environment record is refused; a walk gets a note;
    the credential source's value is never a reason."""

    maxDiff = None

    def setUp(self):
        self.pre = record_pre()
        self.ct = bound_checker()
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.take = tmp / "take"
        shutil.copytree(TAKE, self.take)

    # ---- helpers ---------------------------------------------------------------------------------------

    def record(self) -> dict:
        return json.loads((self.take / "environment.json").read_text())

    def edit(self, fn, rebind: bool = True) -> None:
        rec = self.record()
        fn(rec)
        write_record(self.take, rec, rebind)

    def ledger(self) -> dict:
        return json.loads((self.take / "driver-ledger.json").read_text())

    def problems(self, row_commit: str | None = ROW_COMMIT) -> list[str]:
        with injected(self.ct, self.pre):
            return self.ct.environment_problems(self.take / "transcript.jsonl", self.ledger(), self.pre, row_commit)

    def checked(self, is_walk: bool = False, folder: Path | None = None) -> tuple[list[str], str]:
        folder = folder or self.take
        ct = load_check_take("gap_check_take_environment_walk") if is_walk else self.ct
        buf = io.StringIO()
        with injected(ct, self.pre), contextlib.redirect_stdout(buf):
            got = ct.check(folder / "transcript.jsonl", ROW["task"], ROW["half"],
                           None if is_walk else 0, is_walk)
        return got, buf.getvalue()

    def assertRefused(self, phrase: str, problems: list[str] | None = None) -> None:
        got = self.problems() if problems is None else problems
        self.assertTrue(any(p.startswith("[environment-record] ") and phrase in p for p in got),
                        f"no [environment-record] refusal saying {phrase!r}; got:\n" + "\n".join(got))

    # ---- the whole record ------------------------------------------------------------------------------

    def test_a_whole_bound_record_passes_and_the_take_is_valid(self):
        self.assertEqual(self.problems(), [], "the fixture's record was refused")
        got, _ = self.checked()
        self.assertEqual(got, [], "the valid take was refused:\n" + "\n".join(got))

    def test_a_take_with_no_record_is_refused_through_the_checker(self):
        (self.take / "environment.json").unlink()
        got, _ = self.checked()
        self.assertTrue(any(p.startswith("[environment-record] no environment.json") for p in got),
                        "a take with no environment record was not refused:\n" + "\n".join(got))

    def test_a_pre_registration_without_the_block_refuses_rather_than_passes(self):
        del self.pre["environment_record"]
        self.assertRefused("carries no environment_record block")

    def test_an_unreadable_record_is_refused(self):
        write_record(self.take, b"{not json\n")
        self.assertRefused("is unreadable")

    def test_a_record_that_is_not_an_object_is_refused(self):
        write_record(self.take, b"[]\n")
        self.assertRefused("holds a list, not the object the driver writes")

    def test_a_record_missing_a_key_or_carrying_another_is_refused(self):
        self.edit(lambda r: r.pop("stripped_names"))
        self.assertRefused("missing ['stripped_names']")
        shutil.copy2(TAKE / "environment.json", self.take / "environment.json")
        shutil.copy2(TAKE / "driver-ledger.json", self.take / "driver-ledger.json")
        self.edit(lambda r: r.update(total_cost_usd=0))
        self.assertRefused("1 not in the schema ['total_cost_usd']")

    # ---- the vocabulary and the names ------------------------------------------------------------------

    def test_name_patterns_other_than_the_draft_are_refused(self):
        self.edit(lambda r: r["name_patterns"].update(generic=["SECRET"]))
        self.assertRefused("name patterns other than the pre-registration's")

    def test_a_name_that_is_not_name_shaped_is_refused(self):
        self.edit(lambda r: r["names_present"].append({"name": "aws_region", "matched_by": "harness"}))
        self.assertRefused("entry 3 of names_present is not a variable name")

    def test_a_name_matching_no_pattern_is_refused(self):
        self.edit(lambda r: r["names_present"].append({"name": "SHELL_LEVEL", "matched_by": "generic"}))
        self.assertRefused("entry 3 of names_present matches no published pattern")

    def test_a_wrong_matched_by_is_refused(self):
        def flip(r):
            r["names_present"][2]["matched_by"] = "harness"   # GITHUB_TOKEN: the generic shape only
        self.edit(flip)
        self.assertRefused("names_present records GITHUB_TOKEN as matched by 'harness'")

    def test_a_value_written_where_a_name_belongs_is_refused_without_printing_it(self):
        self.edit(lambda r: r["names_present"].append({"name": PLANTED_VALUE, "matched_by": "generic"}))
        got = self.problems()
        self.assertRefused("a value written where a name belongs", got)
        self.assertFalse([p for p in got if PLANTED_VALUE in p], "the refusal printed what it refused")

    def test_a_stripped_name_from_the_published_vocabulary_is_refused(self):
        self.edit(lambda r: r.update(stripped_names=["ANTHROPIC_API_KEY"]))
        self.assertRefused("a login or billing variable is never stripped")

    def test_a_record_stripping_exactly_the_twelve_names_passes(self):
        """J4's list holds CLAUDE_CODE_MESSAGING_TOKEN, which the generic shape matches; it is still strippable."""
        self.assertIn("CLAUDE_CODE_MESSAGING_TOKEN", STRIPPED_ENV)
        self.assertEqual(self.pre["driver_constants"]["stripped_env"], STRIPPED_ENV)
        self.edit(lambda r: r.update(stripped_names=sorted(STRIPPED_ENV)))
        got = self.problems()
        self.assertEqual(got, [], "a record stripping exactly the twelve names was refused:\n" + "\n".join(got))

    def test_a_harness_or_fixed_list_name_is_never_strippable_even_when_listed(self):
        self.pre["driver_constants"]["stripped_env"] = STRIPPED_ENV + ["ANTHROPIC_FOO"]
        self.edit(lambda r: r.update(stripped_names=["ANTHROPIC_FOO"]))
        self.assertRefused("stripped_names holds ANTHROPIC_FOO, which the published vocabulary names")

        planted = "PLANTED_BILLING_SWITCH"          # on a fixed list, and matched by no pattern
        self.assertIsNone(self.ct.matched_by(planted, ENVIRONMENT_RECORD["name_patterns"]))
        self.pre["environment_record"]["billing_route_variables"].append(planted)
        self.pre["driver_constants"]["stripped_env"] = STRIPPED_ENV + [planted]

        def strip_listed(r):
            r["billing_route_variables"][planted] = "absent"
            r["stripped_names"] = [planted]
        shutil.copy2(TAKE / "environment.json", self.take / "environment.json")
        self.edit(strip_listed)
        self.assertRefused(f"stripped_names holds {planted}, which the published vocabulary names")

    def test_the_checker_and_the_driver_agree_on_what_is_never_stripped(self):
        """Drift: check_take's never-stripped decision equals drive.never_stripped_problems' on every name."""
        spec = importlib.util.spec_from_file_location("gap_drive_environment_check", HERE / "drive.py")
        drive = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(drive)
        fixed = {n for key in ("api_key_variables", "billing_route_variables", "subscription_token_variables")
                 for n in ENVIRONMENT_RECORD[key]}
        planted = {"GITHUB_TOKEN": False, "ANTHROPIC_FOO": True, "ANTHROPIC_API_KEY": True}
        draft = self.ct.prereg.load()["driver_constants"]["stripped_env"]
        self.assertTrue(draft, "the draft names no stripped_env; this compared nothing")
        for name in list(draft) + list(planted):
            with self.subTest(name=name):
                ours = self.ct.never_stripped(name, ENVIRONMENT_RECORD["name_patterns"], fixed)
                theirs = bool(drive.never_stripped_problems([name]))
                self.assertEqual(ours, theirs, f"check_take says {ours}, drive.py says {theirs}")
                if name in planted:
                    self.assertEqual(ours, planted[name])

    def test_a_stripped_name_the_driver_does_not_strip_is_refused(self):
        self.edit(lambda r: r.update(stripped_names=["PYTHONPATH"]))
        self.assertRefused("driver_constants.stripped_env does not list")

    # ---- the bindings ----------------------------------------------------------------------------------

    def test_another_sessions_id_is_refused(self):
        self.edit(lambda r: r.update(session_id=str(uuid.uuid4())))
        self.assertRefused("is not this transcript's")

    def test_a_take_with_no_transcript_is_bound_to_its_ledgers_session_id(self):
        """run.py and check_results.py --ledger grade a take with no transcript from its ledger alone."""
        (self.take / "transcript.jsonl").unlink()
        self.assertEqual(self.problems(), [], "a no-transcript take whose record names the ledger's session "
                                              "was refused")
        self.edit(lambda r: r.update(session_id=str(uuid.uuid4())))
        got = self.problems()
        self.assertTrue(any("is not the ledger's (no transcript sits beside it)" in p for p in got),
                        "a no-transcript take's record naming another session was not refused:\n" + "\n".join(got))

    def test_another_rows_commit_is_refused(self):
        self.edit(lambda r: r.update(row_commit="0" * 40))
        self.assertRefused("the record belongs to another row")

    def test_a_record_the_ledger_does_not_bind_is_refused(self):
        self.edit(lambda r: r.update(record="edited after the take"), rebind=False)
        self.assertRefused("the driver ledger does not record environment.json with the sha256 of its bytes")

    def test_another_harness_version_is_refused(self):
        self.edit(lambda r: r.update(claude_version="2.1.300 (Claude Code)"))
        self.assertRefused("records harness '2.1.300 (Claude Code)'")

    # ---- the three fixed lists -------------------------------------------------------------------------

    def test_an_api_key_set_edited_to_hide_a_key_is_refused(self):
        def hide(r):
            r["api_key_variables"]["ANTHROPIC_API_KEY"] = "set"
            r["names_present"] = sorted(r["names_present"] + [{"name": "ANTHROPIC_API_KEY", "matched_by": "harness"}],
                                        key=lambda e: e["name"])
        self.edit(hide)
        self.assertRefused("records api_key_set False and its own api_key_variables has name set")
        self.edit(lambda r: r.update(api_key_set=True))
        self.assertEqual(self.problems(), [], "a consistent record with a key set was refused; the driver "
                                               "stops that run, and this check is about the record")

    def test_a_billing_route_flag_that_disagrees_with_its_list_is_refused(self):
        def route(r):
            r["billing_route_variables"]["CLAUDE_CODE_USE_BEDROCK"] = "set"
            r["names_present"] = sorted(r["names_present"] + [{"name": "CLAUDE_CODE_USE_BEDROCK",
                                                              "matched_by": "harness"}], key=lambda e: e["name"])
        self.edit(route)
        self.assertRefused("records billing_route_set False and its own billing_route_variables has name set")

    def test_a_present_name_recorded_absent_is_refused(self):
        self.edit(lambda r: r["subscription_token_variables"].update(CLAUDE_CODE_OAUTH_TOKEN="absent"))
        self.assertRefused("names_present lists CLAUDE_CODE_OAUTH_TOKEN and environment.json's "
                           "subscription_token_variables records it absent")

    def test_each_fixed_list_incomplete_or_with_an_extra_name_is_refused(self):
        for key, name in (("api_key_variables", "ANTHROPIC_AUTH_TOKEN"),
                          ("billing_route_variables", "ANTHROPIC_BASE_URL"),
                          ("subscription_token_variables", "CLAUDE_CODE_SESSION_ACCESS_TOKEN")):
            with self.subTest(list=key):
                shutil.copy2(TAKE / "environment.json", self.take / "environment.json")
                self.edit(lambda r: r[key].pop(name))
                self.assertRefused(f"{key} is not exactly the pre-registered list: missing ['{name}']")
                shutil.copy2(TAKE / "environment.json", self.take / "environment.json")
                self.edit(lambda r: r[key].update(ANTHROPIC_OTHER_NAME="absent"))
                self.assertRefused(f"{key} is not exactly the pre-registered list: missing [], 1 name(s) not on it")

    def test_a_state_outside_absent_empty_set_is_refused_without_printing_it(self):
        self.edit(lambda r: r["api_key_variables"].update(ANTHROPIC_API_KEY=PLANTED_VALUE))
        got = self.problems()
        self.assertRefused("in a state other than absent, empty or set", got)
        self.assertFalse([p for p in got if PLANTED_VALUE in p], "the refusal printed the state it refused")

    # ---- the credential source -------------------------------------------------------------------------

    def test_per_turn_not_one_to_one_with_the_ledger_is_refused(self):
        self.edit(lambda r: r["credential_source"]["per_turn"].pop())
        self.assertRefused("they are not one to one by (n, recovery)")
        shutil.copy2(TAKE / "environment.json", self.take / "environment.json")
        self.edit(lambda r: r["credential_source"]["per_turn"][1].update(recovery=True))
        self.assertRefused("they are not one to one by (n, recovery)")

    def test_a_recovery_turn_is_matched_by_its_own_row(self):
        led = self.ledger()
        led["turns"].insert(1, {"n": 1, "sent": "run", "recovery": True, "exit": 0})
        (self.take / "driver-ledger.json").write_text(json.dumps(led, indent=2) + "\n")
        self.edit(lambda r: r["credential_source"]["per_turn"].insert(
            1, {"n": 1, "recovery": True, "exit": 0, "apiKeySource": None}))
        self.assertEqual(self.problems(), [])

    def test_a_non_subscription_credential_source_is_never_a_refusal(self):
        """A refusal frees the slot; a check that refused on the source's value would be a retake route."""
        for source in ("ANTHROPIC_API_KEY", "none", None):
            with self.subTest(source=source):
                def set_source(r):
                    for t in r["credential_source"]["per_turn"]:
                        t["apiKeySource"] = source
                    r["credential_source"]["reported"] = source
                self.edit(set_source)
                got, _ = self.checked()
                self.assertEqual(got, [], f"the take was refused for reporting {source!r}:\n" + "\n".join(got))

    # ---- walks -----------------------------------------------------------------------------------------

    def test_a_walk_without_a_record_gets_a_note_and_stays_valid(self):
        got, printed = self.checked(is_walk=True, folder=WALK)
        self.assertEqual(got, [], "\n".join(got))
        self.assertIn("NOTE     [environment-record] no environment.json", printed)

    def test_a_walk_with_a_broken_record_gets_a_note_and_stays_valid(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        walk = tmp / "walk"
        shutil.copytree(WALK, walk)
        write_record(walk, b"[]\n")
        got, printed = self.checked(is_walk=True, folder=walk)
        self.assertEqual(got, [], "a walk was refused for its environment record:\n" + "\n".join(got))
        self.assertIn("NOTE     [environment-record] environment.json holds a list", printed)

    # ---- end to end, through the command line (structural lesson 12) ----------------------------------

    def test_a_walk_without_a_record_through_the_command_line(self):
        r = run_cli(str(HERE / "check_take.py"), str(WALK / "transcript.jsonl"),
                    "--task", ROW["task"], "--half", ROW["half"], "--walk")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("NOTE     [environment-record]", r.stdout)
        self.assertIn("valid — every operator-side check passed", r.stdout)

    def box(self) -> tuple[Path, str]:
        """A throwaway repository holding this study and one committed row, and the fixture take re-bound
        to that row's commit. Returns (the copied check_take.py, the attempt folder)."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        root = tmp / "box" / "repository"
        study_dir = root / "evals" / HERE.name

        def leave_out_live(src, names):
            return [n for n in names if n in LIVE_NAMES] if Path(src) == HERE else [n for n in names if n == "__pycache__"]

        shutil.copytree(HERE, study_dir, ignore=leave_out_live)
        shutil.copy2(REPO / "evals" / "transcript.py", root / "evals" / "transcript.py")
        pre = {k: v for k, v in self.pre.items() if not k.startswith("_")}
        (study_dir / "prereg-draft.json").write_text(json.dumps(pre, indent=2, ensure_ascii=False) + "\n")
        (study_dir / "takes.json").write_text(json.dumps({"rows": [ROW]}, indent=2) + "\n")

        def git(*args: str) -> str:
            r = subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                                "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
            if r.returncode != 0:
                raise AssertionError(f"git {args[0]} failed in the throwaway repository: {r.stderr.strip()}")
            return r.stdout.strip()

        scratch_git.init(root)
        git("add", "--", f"evals/{HERE.name}/takes.json")
        git("commit", "-q", "--no-verify", "-m", "row 0")
        sha = git("log", "-1", "--format=%H", "--", f"evals/{HERE.name}/takes.json")

        attempt = tmp / "attempt"
        shutil.copytree(TAKE, attempt)
        with injected(self.ct, self.pre):
            old_sid = self.ct.takes_mod.session_id_for(ROW_COMMIT)
            new_sid = self.ct.takes_mod.session_id_for(sha)
        swaps = ((old_sid, new_sid), (self.ct.neutral_name(old_sid), self.ct.neutral_name(new_sid)), (ROW_COMMIT, sha))
        for name in ("transcript.jsonl", "driver-ledger.json", "environment.json"):
            text = (attempt / name).read_text()
            for a, b in swaps:
                text = text.replace(a, b)
            (attempt / name).write_text(text)
        body = (attempt / "environment.json").read_bytes()
        led = json.loads((attempt / "driver-ledger.json").read_text())
        led["environment"]["sha256"] = hashlib.sha256(body).hexdigest()
        (attempt / "driver-ledger.json").write_text(json.dumps(led, indent=2) + "\n")

        # The pinned tree the instruction file is bound to: the file the fixture session recorded.
        first = next(json.loads(ln) for ln in (attempt / "transcript.jsonl").read_text().splitlines()
                     if '"instructions"' in ln)
        (root / "gars").mkdir(parents=True)
        (root / "gars" / "CLAUDE.md").write_text(first["attachment"]["files"][0]["content"])
        return study_dir / "check_take.py", attempt

    def test_a_graded_take_through_the_command_line(self):
        checker, attempt = self.box()
        argv = [str(checker), str(attempt / "transcript.jsonl"), "--task", ROW["task"], "--half", ROW["half"],
                "--row", "0"]
        ok = run_cli(*argv)
        self.assertEqual(ok.returncode, 0, "the re-bound valid take is not valid through the command line:\n"
                         + ok.stdout + ok.stderr)
        (attempt / "environment.json").unlink()
        gone = run_cli(*argv)
        self.assertEqual(gone.returncode, 1, gone.stdout + gone.stderr)
        self.assertIn("[environment-record] no environment.json", gone.stdout,
                      "a take with no environment record was not refused through the command line")


if __name__ == "__main__":
    unittest.main()
