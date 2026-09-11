#!/usr/bin/env python3
"""Break each guard on purpose, in a throwaway copy, and assert it goes red.

    python3 evals/gap-study/test_harness.py --mutations

WHY EVERY ONE OF THESE EXISTS. A guard nobody has watched fail is a guard nobody knows is wired up.
This study has already shipped four of them: a language linter that scanned its own pattern table, a
contract checker whose first mutation run read the wrong exit code, a write detector that called awk
comparisons writes, and a test runner that reported success while tests failed. Each looked correct
and each was found by making it fail on demand.

EVERY MUTATION RUNS IN A COPY. The study tree is copied to a temporary directory, the mutation is
applied there, the guard is run there, and the copy is thrown away. Nothing mutates the real tree,
so there is no restore step to get wrong -- the failure mode where a mutation is left behind because
the revert did not run cannot happen here.

Where a guard reads git history, the copy is made into a real repository with real commits, because
a check that reads history and is handed none passes vacuously, which is the opposite of what a
mutation run is for.

WHAT IS NOT HERE, AND WHY. Two of the pre-registered mutations cannot be run yet and say so rather
than being quietly dropped: anything about a local transcript, because the local tier was dropped at
gate 2 and there will be no local take; and anything requiring a committed take, because no take has
run before the freeze. They are listed as `not applicable` with their reason, and a reader can see
the difference between a guard that passed and one that was never driven.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def _run(argv: list[str], cwd: Path) -> int:
    return subprocess.run([sys.executable, *argv], capture_output=True, text=True,
                          cwd=str(cwd)).returncode


class Sandbox:
    """A throwaway copy of the study, optionally inside a real git repository."""

    def __init__(self, git: bool = False):
        self.git = git
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "evals").mkdir(parents=True)
        shutil.copytree(HERE, self.root / "evals" / "gap-study")
        # the first study's readers, and the files the carried task is bound to: its driver (the
        # source of the carried script), its pre-registration (the pins) and its pilot ledgers
        for f in ("transcript.py", "stated_count.py", "drive.py", "prereg.json", "take-map.json"):
            src = REPO / "evals" / f
            if src.is_file():
                shutil.copy2(src, self.root / "evals" / f)
        for half in ("positive", "control"):
            src = REPO / "evals" / "transcripts" / "confounded-refusal" / half / "driver-ledger.json"
            if src.is_file():
                dst = self.root / "evals" / "transcripts" / "confounded-refusal" / half / "driver-ledger.json"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        # the system under test, for the fixture guard
        gars = REPO / "gars"
        if gars.is_dir():
            (self.root / "gars").mkdir()
            shutil.copytree(gars / "_system", self.root / "gars" / "_system")
        if git:
            subprocess.run(["git", "init", "-q"], cwd=self.root, capture_output=True)
            subprocess.run(["git", "add", "-A"], cwd=self.root, capture_output=True)
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-qm", "base"], cwd=self.root, capture_output=True)

    @property
    def study(self) -> Path:
        return self.root / "evals" / "gap-study"

    def commit(self, msg: str) -> str:
        subprocess.run(["git", "add", "-A"], cwd=self.root, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", msg],
                       cwd=self.root, capture_output=True)
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root,
                              capture_output=True, text=True).stdout.strip()

    def run(self, argv: list[str]) -> int:
        return _run(argv, self.root)

    def close(self):
        self.tmp.cleanup()


# --------------------------------------------------------------------------- mutations

def m_edited_contract_quote(s: Sandbox) -> tuple[int, str]:
    """One character changed in a pinned contract sentence."""
    p = s.study / "contract_quotes.json"
    d = json.loads(p.read_text())
    d["quotes"][0]["text"] = d["quotes"][0]["text"] + "!"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return s.run([str(s.study / "contracts.py"), "--check"]), "contracts.py --check"


def m_emptied_quote_table(s: Sandbox) -> tuple[int, str]:
    """The quote table emptied: nothing checked is not a pass."""
    p = s.study / "contract_quotes.json"
    d = json.loads(p.read_text())
    d["quotes"] = []
    p.write_text(json.dumps(d, indent=2))
    return s.run([str(s.study / "contracts.py"), "--check"]), "contracts.py --check"


def m_banned_word_in_a_results_file(s: Sandbox) -> tuple[int, str]:
    """A results file carrying a rate word."""
    (s.study / "results").mkdir(exist_ok=True)
    (s.study / "results" / "doctored.json").write_text(
        json.dumps({"note": "the model held this task reliably across every take"}, indent=2))
    return (s.run([str(s.study / "lint_language.py"), str(s.study)]),
            "lint_language.py over the study")


def m_percentage_in_a_results_file(s: Sandbox) -> tuple[int, str]:
    (s.study / "results").mkdir(exist_ok=True)
    (s.study / "results" / "doctored.json").write_text(
        json.dumps({"note": "held in 67% of takes"}, indent=2))
    return (s.run([str(s.study / "lint_language.py"), str(s.study)]),
            "lint_language.py over the study")


def m_excusal_pinned_to_the_wrong_text(s: Sandbox) -> tuple[int, str]:
    """An excused line whose text has since changed must stop being excused."""
    p = s.study / "language-allowlist.json"
    d = json.loads(p.read_text())
    if not d.get("excused"):
        return 1, "language-allowlist.json (no excusal on record; nothing to break)"
    # The INTERIOR of the line, not its trailing whitespace. The guard compares rstripped text on
    # purpose -- a trailing space should not retire somebody's ruling -- so appending one mutates
    # nothing and the first version of this mutation came back green against a working guard.
    txt = d["excused"][0]["line_text"]
    d["excused"][0]["line_text"] = txt.replace("gated", "GATED", 1) if "gated" in txt \
        else txt.rstrip() + " AND SOMETHING ELSE"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return (s.run([str(s.study / "lint_language.py"), str(s.study)]),
            "lint_language.py over the study")


def m_take_index_outside_n(s: Sandbox) -> tuple[int, str]:
    """A take index outside 1..n, with n left where the pre-registration fixed it.

    THIS MUTATION USED TO PASS FOR THE WRONG REASON. It raised n to 4 and then registered take 4 --
    which is legal under n = 4, so the guard should have ALLOWED it. It came back red anyway,
    because the sandbox had no git repository and takes.py died reading the ledger's status before
    it reached any check.

    A false red is worth no more than a false green: both say a guard fired when it did not. The
    sandbox now has a real repository, and the mutation asks the question it meant to ask.
    """
    return (s.run([str(s.study / "takes.py"), "--add", "--task", "scope-read", "--half",
                   "positive", "--model", "claude-opus-5", "--take", "4", "--allow-draft"]),
            "takes.py --add with take 4 where n is 3")


def m_fourth_graded_take(s: Sandbox) -> tuple[int, str]:
    """A fourth take in a cell where n is three."""
    p = s.study / "takes.json"
    rows = [{"task": "scope-read", "half": "positive", "model": "claude-opus-5", "take": k,
             "order_index": k, "fixture_sha": "x",
             "environment_class": "claude-subscription-headless"} for k in (1, 2, 3)]
    p.write_text(json.dumps({"role": "test", "rows": rows}, indent=2))
    return (s.run([str(s.study / "takes.py"), "--add", "--task", "scope-read", "--half",
                   "positive", "--model", "claude-opus-5", "--take", "1", "--allow-draft"]),
            "takes.py --add a fourth take")


def m_tampered_namespace(s: Sandbox) -> tuple[int, str]:
    p = s.study / "prereg-draft.json"
    d = json.loads(p.read_text())
    d["session_namespace"]["uuid"] = "00000000-0000-5000-8000-000000000000"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return s.run([str(s.study / "takes.py"), "--plan"]), "takes.py --plan"


def m_two_rows_in_one_commit(s: Sandbox) -> tuple[int, str]:
    """Two rows sharing a commit would share a session id."""
    rows = [{"task": "scope-read", "half": "positive", "model": "claude-opus-5", "take": k,
             "order_index": k, "fixture_sha": "x",
             "environment_class": "claude-subscription-headless"} for k in (1, 2)]
    (s.study / "takes.json").write_text(json.dumps({"role": "test", "rows": rows}, indent=2))
    s.commit("take: two at once")
    return s.run([str(s.study / "takes.py"), "--audit"]), "takes.py --audit"


def m_shallow_history(s: Sandbox) -> tuple[int, str]:
    """A ledger check handed no history must refuse, not pass."""
    shutil.rmtree(s.root / ".git")
    return (s.run([str(s.study / "check_results.py"), "--ledger"]),
            "check_results.py --ledger with no history")


def m_fixture_names_the_task(s: Sandbox) -> tuple[int, str]:
    """A fixture that tells the agent what is being measured."""
    gen = s.study / "fixtures" / "gen_source.py"
    src = gen.read_text().replace(
        'b"Operator     core facility\\n"',
        'b"Operator     scope-read evaluation fixture\\n"')
    gen.write_text(src)
    code = s.run([str(s.study / "fixtures" / "check_fixture.py"), "--all"])
    if code != 0:
        return code, "check_fixture.py --all"
    # the front-door check may not read the runsheet; the leak sweep is the guard that must
    return _sweep_says_leak(s), "neutralise.sweep over the built fixture"


def _sweep_says_leak(s: Sandbox) -> int:
    out = tempfile.mkdtemp()
    subprocess.run([sys.executable, str(s.study / "fixtures" / "gen_source.py"),
                    "--variant", "plain", "--seed", "20260908", "--out", out],
                   capture_output=True)
    sweep = REPO / "evals" / "fixtures" / "neutralise.py"
    if not sweep.is_file():
        return 1
    code = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(sweep.parent)!r}); import neutralise; "
         f"from pathlib import Path; "
         f"leaks = neutralise.sweep(Path({out!r})); "
         f"print(len(leaks)); sys.exit(1 if leaks else 0)"],
        capture_output=True, text=True).returncode
    shutil.rmtree(out, ignore_errors=True)
    return code


def m_manifest_inside_the_fixture(s: Sandbox) -> tuple[int, str]:
    """A file describing the fixture, sitting in the fixture."""
    out = tempfile.mkdtemp()
    code = subprocess.run(
        [sys.executable, str(s.study / "fixtures" / "gen_source.py"), "--variant", "plain",
         "--seed", "20260908", "--out", out, "--manifest-out", str(Path(out) / "M.json")],
        capture_output=True, text=True).returncode
    shutil.rmtree(out, ignore_errors=True)
    return code, "gen_source.py --manifest-out inside --out"


def m_take_with_no_agent_turn(s: Sandbox) -> tuple[int, str]:
    """A transcript with no agent turn is a rehearsal, never a take."""
    walk = s.study / "walks" / "scope-read" / "1" / "transcript.jsonl"
    if not walk.is_file():
        return 1, "check_take.py (no walk to mutate)"
    keep = [ln for ln in walk.read_text().splitlines()
            if '"type":"assistant"' not in ln.replace(" ", "")]
    p = Path(tempfile.mkdtemp()) / "t.jsonl"
    p.write_text("\n".join(keep) + "\n")
    return (s.run([str(s.study / "check_take.py"), str(p), "--task", "scope-read",
                   "--half", "positive", "--walk"]),
            "check_take.py on a transcript with no agent turn")


def m_leaked_word_in_an_operator_turn(s: Sandbox) -> tuple[int, str]:
    walk = s.study / "walks" / "scope-read" / "1" / "transcript.jsonl"
    if not walk.is_file():
        return 1, "check_take.py (no walk to mutate)"
    lines, done = [], False
    for ln in walk.read_text().splitlines():
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            lines.append(ln)
            continue
        if not done and rec.get("type") == "user":
            msg = rec.get("message") or {}
            if isinstance(msg.get("content"), str):
                msg["content"] += " (this is an evaluation)"
                done = True
                ln = json.dumps(rec)
        lines.append(ln)
    p = Path(tempfile.mkdtemp()) / "t.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return (s.run([str(s.study / "check_take.py"), str(p), "--task", "scope-read",
                   "--half", "positive", "--walk"]),
            "check_take.py on a take with a leaked word")


def m_grading_against_a_draft(s: Sandbox) -> tuple[int, str]:
    """run.py must refuse while the pre-registration is a draft."""
    return s.run([str(s.study / "run.py"), "--all"]), "run.py --all against a draft"


def m_run_tree_keeps_what_it_excludes(s: Sandbox) -> tuple[int, str]:
    """The checkout built without its exclusions: the study is back in front of the agent."""
    p = s.study / "drive.py"
    text = p.read_text()
    mutated = text.replace("*spec], check=True", "], check=True")
    if mutated == text:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    p.write_text(mutated)
    return (s.run([str(s.study / "test_harness.py"), "TheRunTreeCarriesNothing"]),
            "test_harness.py TheRunTreeCarriesNothing")


def m_run_tree_named_for_the_study(s: Sandbox) -> tuple[int, str]:
    """The checkout's name says what the take is, and the agent is shown its working directory."""
    p = s.study / "drive.py"
    text = p.read_text()
    mutated = text.replace("return Path(tempfile.gettempdir()).resolve() / neutral_name(session_id)",
                           "return Path(tempfile.gettempdir()).resolve() / "
                           "('gap-study-' + neutral_name(session_id))")
    if mutated == text:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    p.write_text(mutated)
    return (s.run([str(s.study / "test_harness.py"), "TheRunTreeCarriesNothing"]),
            "test_harness.py TheRunTreeCarriesNothing")


def m_study_names_dropped_from_the_leak_list(s: Sandbox) -> tuple[int, str]:
    """Review 11, F2: a leak list that cannot name the study reports clean on a leaked walk."""
    p = s.study / "prereg-draft.json"
    d = json.loads(p.read_text())
    d["leak_words"] = [w for w in d["leak_words"]
                       if w not in ("gap-study", "gap study", "prereg", "pre-registration",
                                    "pre-registered")]
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return (s.run([str(s.study / "test_harness.py"), "TheLeakCheckReadsEveryChannel"]),
            "test_harness.py TheLeakCheckReadsEveryChannel")


def m_published_walk_carries_the_email(s: Sandbox) -> tuple[int, str]:
    """Ruling 10: a published transcript that still carries the account's email address field."""
    p = s.study / "walks" / "number-fidelity" / "2" / "transcript.jsonl"
    out, applied = [], False
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            out.append(line)
            continue
        att = rec.get("attachment") if isinstance(rec, dict) else None
        if isinstance(att, dict) and att.get("type") == "session_context":
            att.setdefault("context", {})["userEmail"] = "The user's email address is someone@example.com."
            out.append(json.dumps(rec, ensure_ascii=False))
            applied = True
        else:
            out.append(line)
    if not applied:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    p.write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    return (s.run([str(s.study / "check_take.py"), str(p), "--task", "number-fidelity",
                   "--half", "control", "--walk"]),
            "check_take.py on a published walk carrying the email field")


def m_carried_line_edited(s: Sandbox) -> tuple[int, str]:
    """A carried operator line edited in the draft: the projection is no longer script()."""
    p = s.study / "prereg-draft.json"
    d = json.loads(p.read_text())
    t = next(t for t in d["tasks"] if t["id"] == "confounded-design")
    step = t["positive"]["operator_script"][1]
    if step["line"] != "05":
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    step["line"] = "5"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return (s.run([str(s.study / "test_harness.py"), "CarriedScriptIsTheFirstStudys"]),
            "test_harness.py CarriedScriptIsTheFirstStudys")


def m_recovery_read_as_improvisation(s: Sandbox) -> tuple[int, str]:
    """The checker with its recovery allowance removed: the take a recovery rescued is refused."""
    p = s.study / "check_take.py"
    text = p.read_text()
    mutated = text.replace('        if rec:\n            at_most = int(rec.get("at_most", 1))',
                           '        if False:\n            at_most = int(rec.get("at_most", 1))')
    if mutated == text:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    p.write_text(mutated)
    return (s.run([str(s.study / "test_harness.py"), "TheCheckerAdmitsOnlyThePreRegisteredScript"]),
            "test_harness.py TheCheckerAdmitsOnlyThePreRegisteredScript")


def m_carried_marker_compared_exactly(s: Sandbox) -> tuple[int, str]:
    """The driver ignoring a step's declared comparison: no carried marker would ever hold."""
    p = s.study / "drive.py"
    text = p.read_text()
    mutated = text.replace('    if step.get("comparison") == "case-insensitive":\n'
                           '        return marker.lower() in said.lower()\n', '')
    if mutated == text:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    p.write_text(mutated)
    return (s.run([str(s.study / "test_harness.py"), "TheThenStepAndComparisonAreData"]),
            "test_harness.py TheThenStepAndComparisonAreData")


MUTATIONS = [
    ("an edited contract quote", m_edited_contract_quote, True),
    ("an emptied quote table", m_emptied_quote_table, True),
    ("a banned rate word in a results file", m_banned_word_in_a_results_file, False),
    ("a percentage in a results file", m_percentage_in_a_results_file, False),
    ("an excusal pinned to text that changed", m_excusal_pinned_to_the_wrong_text, False),
    ("a take index outside n", m_take_index_outside_n, True),
    ("a fourth graded take", m_fourth_graded_take, True),
    ("a tampered session namespace", m_tampered_namespace, True),
    ("two ledger rows in one commit", m_two_rows_in_one_commit, True),
    ("a ledger check handed no history", m_shallow_history, True),
    ("a fixture that names the task", m_fixture_names_the_task, False),
    ("a manifest written inside the fixture", m_manifest_inside_the_fixture, False),
    ("a take with no agent turn", m_take_with_no_agent_turn, False),
    ("a leaked word in an operator turn", m_leaked_word_in_an_operator_turn, False),
    ("grading against a draft", m_grading_against_a_draft, False),
    ("a checkout that keeps what it excludes", m_run_tree_keeps_what_it_excludes, False),
    ("a checkout named for the study", m_run_tree_named_for_the_study, False),
    ("the study's names dropped from the leak list", m_study_names_dropped_from_the_leak_list, False),
    ("a published walk carrying the email field", m_published_walk_carries_the_email, False),
    ("a carried operator line edited", m_carried_line_edited, False),
    ("a recovery line read as improvisation", m_recovery_read_as_improvisation, False),
    ("a carried marker compared exactly", m_carried_marker_compared_exactly, False),
]

NOT_APPLICABLE = [
    ("a moved threshold after the freeze",
     "a threshold is pinned by the frozen file's own sha256, and nothing is pinned before the "
     "freeze. check_results.py's default check is what catches it, and it already refuses today "
     "because no file carries a sha yet"),
    ("a local transcript with no server log",
     "the local tier was dropped at gate 2, so no local take will exist to mutate"),
    ("a transcript whose session id does not match its row's commit",
     "no take has run before the freeze; check_take.py's binding is unit-tested instead"),
    ("a row committed after its transcript's takes: commit",
     "same reason: there is no takes: commit yet"),
    ("a doctored results file re-graded",
     "no results file exists before the freeze; the regrade path is driven end to end in a "
     "scratch tree with synthetic takes"),
    ("a gars sha differing from the freeze",
     "the freeze has not happened, so there is no pinned sha to differ from"),
    ("a carried fixture whose tree hash differs from the freeze",
     "no fixture pin exists before the freeze; the builder's refusal on a disagreeing pin is "
     "unit-tested instead (TheCarriedFixtureBuilds)"),
]


def run_all() -> int:
    print(f"{len(MUTATIONS)} mutation(s); each applied to a throwaway copy, the guard run there, "
          f"the copy discarded\n")
    failures = []
    for name, fn, needs_git in MUTATIONS:
        s = Sandbox(git=needs_git)
        try:
            code, guard = fn(s)
        except Exception as exc:  # a mutation that cannot even run is a failure of this file
            code, guard = 0, f"raised {exc!r}"
        finally:
            s.close()
        ok = code != 0
        print(f"  {'red ' if ok else 'GREEN'}  exit {code:<3} {name:44} {guard}")
        if not ok:
            failures.append(name)

    print(f"\n{len(NOT_APPLICABLE)} mutation(s) NOT APPLICABLE yet, listed rather than dropped:")
    for name, why in NOT_APPLICABLE:
        print(f"  n/a   {name:44} {why}")

    if failures:
        print(f"\n{len(failures)} guard(s) did NOT go red: {failures}")
        print("A guard that cannot fail is not protecting anything.")
        return 1
    print(f"\nevery one of the {len(MUTATIONS)} guards went red when broken")
    return 0
