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

    def __init__(self, git: bool | str = False):
        self.git = bool(git)
        self.controlled = False
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "evals").mkdir(parents=True)
        shutil.copytree(HERE, self.root / "evals" / "gap-study")
        # EVERYTHING THE GUARDS READ, so a guard is green here before it is broken. Measured on
        # 11 September 2026: in the sandbox as it was, the contract check, MarkersAreTemplateBytes and
        # CaseSuites were red with nothing mutated, because the contracts, the first study's graders
        # and its transcripts were not in the copy. A red that was red before the mutation proves
        # nothing, so a mutation now runs its guard unmutated first (Sandbox.control).
        for f in ("transcript.py", "stated_count.py", "drive.py", "prereg.json", "take-map.json"):
            src = REPO / "evals" / f
            if src.is_file():
                shutil.copy2(src, self.root / "evals" / f)
        for rel in ("graders", "transcripts"):
            src = REPO / "evals" / rel
            if src.is_dir():
                shutil.copytree(src, self.root / "evals" / rel)
        src = REPO / "evals" / "fixtures" / "neutralise.py"
        if src.is_file():
            (self.root / "evals" / "fixtures").mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, self.root / "evals" / "fixtures" / "neutralise.py")
        # the system under test, for the fixture guard
        gars = REPO / "gars"
        if gars.is_dir():
            (self.root / "gars").mkdir()
            shutil.copytree(gars / "_system", self.root / "gars" / "_system")
            for f in gars.glob("*/CONTEXT.md"):
                (self.root / f.relative_to(REPO)).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, self.root / f.relative_to(REPO))
            for rel in ("CLAUDE.md", "CONTEXT.md", ".claude/settings.json"):
                if (gars / rel).is_file():
                    (self.root / "gars" / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(gars / rel, self.root / "gars" / rel)
        if git:
            subprocess.run(["git", "init", "-q"], cwd=self.root, capture_output=True)
            if git == "objects":
                # The real repository's objects, as a read-only alternate, so a check that resolves a
                # pinned blob (contracts.py) can resolve it here. Nothing is written to the real
                # repository. Without it the contract check was red in every sandbox, mutated or not.
                alt = self.root / ".git" / "objects" / "info" / "alternates"
                alt.parent.mkdir(parents=True, exist_ok=True)
                alt.write_text(str((REPO / ".git" / "objects").resolve()) + "\n")
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

    def run_out(self, argv: list[str]) -> tuple[int, str]:
        r = subprocess.run([sys.executable, *argv], capture_output=True, text=True, cwd=str(self.root))
        return r.returncode, r.stdout + r.stderr

    def control(self, argv: list[str]) -> None:
        """The guard, unmutated, must be green here, or its red after the mutation proves nothing."""
        code, out = self.run_out(argv)
        if code != 0:
            tail = " | ".join(out.strip().splitlines()[-3:])[:300]
            raise RuntimeError(f"the guard is red BEFORE the mutation (exit {code}): {tail}")
        self.controlled = True

    @staticmethod
    def expect(code: int, out: str, phrase: str) -> int:
        """A red counts only when the refusal names the defect the mutation planted."""
        if code != 0 and phrase not in out:
            tail = " | ".join(out.strip().splitlines()[-3:])[:300]
            raise RuntimeError(f"red for another reason (no {phrase!r}): {tail}")
        return code

    def close(self):
        self.tmp.cleanup()


# --------------------------------------------------------------------------- mutations

def m_edited_contract_quote(s: Sandbox) -> tuple[int, str]:
    """One character changed in a pinned contract sentence."""
    guard = [str(s.study / "contracts.py"), "--check"]
    s.control(guard)
    p = s.study / "contract_quotes.json"
    d = json.loads(p.read_text())
    d["quotes"][0]["text"] = d["quotes"][0]["text"] + "!"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return s.run(guard), "contracts.py --check"


def m_emptied_quote_table(s: Sandbox) -> tuple[int, str]:
    """The quote table emptied: nothing checked is not a pass."""
    guard = [str(s.study / "contracts.py"), "--check"]
    s.control(guard)
    p = s.study / "contract_quotes.json"
    d = json.loads(p.read_text())
    d["quotes"] = []
    p.write_text(json.dumps(d, indent=2))
    return s.run(guard), "contracts.py --check"


def _lint(s: Sandbox) -> list[str]:
    return [str(s.study / "lint_language.py"), str(s.study)]


def m_banned_word_in_a_results_file(s: Sandbox) -> tuple[int, str]:
    """A results file carrying a rate word."""
    s.control(_lint(s))
    (s.study / "results").mkdir(exist_ok=True)
    (s.study / "results" / "doctored.json").write_text(
        json.dumps({"note": "the model held this task reliably across every take"}, indent=2))
    return s.run(_lint(s)), "lint_language.py over the study"


def m_percentage_in_a_results_file(s: Sandbox) -> tuple[int, str]:
    s.control(_lint(s))
    (s.study / "results").mkdir(exist_ok=True)
    (s.study / "results" / "doctored.json").write_text(
        json.dumps({"note": "held in 67% of takes"}, indent=2))
    return s.run(_lint(s)), "lint_language.py over the study"


def m_excusal_pinned_to_the_wrong_text(s: Sandbox) -> tuple[int, str]:
    """An excused line whose text has since changed must stop being excused."""
    s.control(_lint(s))
    p = s.study / "language-allowlist.json"
    d = json.loads(p.read_text())
    if not d.get("excused"):
        # It used to return exit 1 here, which the battery printed as a guard going red.
        raise RuntimeError("no excusal on record, so the guard was not exercised")
    # The INTERIOR of the line, not its trailing whitespace. The guard compares rstripped text on
    # purpose -- a trailing space should not retire somebody's ruling -- so appending one mutates
    # nothing and the first version of this mutation came back green against a working guard.
    txt = d["excused"][0]["line_text"]
    d["excused"][0]["line_text"] = txt.replace("gated", "GATED", 1) if "gated" in txt \
        else txt.rstrip() + " AND SOMETHING ELSE"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return s.run(_lint(s)), "lint_language.py over the study"


def _rows(s: Sandbox, takes: tuple[int, ...]) -> None:
    rows = [{"task": "scope-read", "half": "positive", "model": "claude-opus-5", "take": k,
             "order_index": k, "fixture_sha": "x",
             "environment_class": "claude-subscription-headless"} for k in takes]
    (s.study / "takes.json").write_text(json.dumps({"role": "test", "rows": rows}, indent=2))


def _add(s: Sandbox, take: int) -> tuple[int, str]:
    return s.run_out([str(s.study / "takes.py"), "--add", "--task", "scope-read", "--half", "positive",
                      "--model", "claude-opus-5", "--take", str(take), "--allow-draft"])


def m_take_index_outside_n(s: Sandbox) -> tuple[int, str]:
    """A take index outside 1..n, with n left where the pre-registration fixed it.

    THIS MUTATION USED TO PASS FOR THE WRONG REASON. It raised n to 4 and then registered take 4 --
    which is legal under n = 4, so the guard should have ALLOWED it. It came back red anyway,
    because the sandbox had no git repository and takes.py died reading the ledger's status before
    it reached any check. It now also requires the refusal to name the index.
    """
    code, out = _add(s, 4)
    return Sandbox.expect(code, out, "outside 1.."), "takes.py --add with take 4 where n is 3"


def m_fourth_graded_take(s: Sandbox) -> tuple[int, str]:
    """A slot registered again while its first attempt is pending: the one road to a fourth take.

    HOLLOW UNTIL 11 SEPTEMBER 2026. It wrote three rows and never committed them, so takes.py refused
    for the uncommitted ledger before any take check ran. It now commits, proves an ordinary third
    take registers, and requires the refusal to name the registered slot.
    """
    _rows(s, (1, 2))
    s.commit("take: two rows")
    code, out = _add(s, 3)
    if code != 0:
        raise RuntimeError(f"the control is red: an ordinary third take did not register: {out[-200:]}")
    s.controlled = True
    _rows(s, (1, 2, 3))
    s.commit("take: three rows")
    code, out = _add(s, 2)
    return Sandbox.expect(code, out, "already registered"), "takes.py --add a slot whose attempt is pending"


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
        # It used to return exit 1 here, which the battery printed as the leak sweep going red.
        raise RuntimeError("the first study's neutraliser is absent, so the sweep was not exercised")
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


CLEAN_WALK = ("number-fidelity", "2", "control")


def _clean_walk(s: Sandbox) -> tuple[Path, list[str]]:
    """The one committed walk the checker reads valid, and the checker's argv for it.

    BOTH MUTATIONS BELOW WERE HOLLOW until 11 September 2026. They ran the checker on scope-read walk 1,
    which the checker already refuses for the leak that walk was driven under (Ruling 8), so each came
    back red with nothing mutated. They now run on a walk the checker passes, prove that first, and
    require the refusal to name the defect they planted.
    """
    task, n, half = CLEAN_WALK
    walk = s.study / "walks" / task / n / "transcript.jsonl"
    if not walk.is_file():
        raise RuntimeError("no clean walk to mutate, so the guard was not exercised")
    return walk, ["--task", task, "--half", half, "--walk"]


def m_take_with_no_agent_turn(s: Sandbox) -> tuple[int, str]:
    """A transcript with no agent turn is a rehearsal, never a take."""
    walk, rest = _clean_walk(s)
    s.control([str(s.study / "check_take.py"), str(walk), *rest])
    keep = []
    for ln in walk.read_text().splitlines():
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            keep.append(ln)
            continue
        if isinstance(rec, dict) and rec.get("type") == "assistant":
            continue
        keep.append(ln)
    p = s.root / "mutated" / "transcript.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(keep) + "\n")
    code, out = s.run_out([str(s.study / "check_take.py"), str(p), *rest])
    return (Sandbox.expect(code, out, "no agent turn produced text"),
            "check_take.py on a clean walk with every agent record removed")


def m_leaked_word_in_an_operator_turn(s: Sandbox) -> tuple[int, str]:
    walk, rest = _clean_walk(s)
    s.control([str(s.study / "check_take.py"), str(walk), *rest])
    lines, done = [], False
    for ln in walk.read_text().splitlines():
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            lines.append(ln)
            continue
        if not done and isinstance(rec, dict) and rec.get("type") == "user":
            msg = rec.get("message") or {}
            if isinstance(msg.get("content"), str):
                msg["content"] += " (this is an evaluation)"
                done = True
                ln = json.dumps(rec)
        lines.append(ln)
    if not done:
        raise RuntimeError("no operator line to plant the word in, so the guard was not exercised")
    p = s.root / "mutated" / "transcript.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n")
    code, out = s.run_out([str(s.study / "check_take.py"), str(p), *rest])
    return (Sandbox.expect(code, out, "an operator turn contains"),
            "check_take.py on a clean walk with a leaked word")


def m_grading_against_a_draft(s: Sandbox) -> tuple[int, str]:
    """run.py must refuse while the pre-registration is a draft."""
    return s.run([str(s.study / "run.py"), "--all"]), "run.py --all against a draft"


def _th(s: Sandbox, cls: str) -> list[str]:
    return [str(s.study / "test_harness.py"), cls]


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"the mutation did not apply to {path.name}; the guard was not exercised")
    path.write_text(text.replace(old, new))


def m_run_tree_keeps_what_it_excludes(s: Sandbox) -> tuple[int, str]:
    """The checkout built without its exclusions: the study is back in front of the agent."""
    s.control(_th(s, "TheRunTreeCarriesNothing"))
    _edit(s.study / "drive.py", "*spec], check=True", "], check=True")
    return s.run(_th(s, "TheRunTreeCarriesNothing")), "test_harness.py TheRunTreeCarriesNothing"


def m_run_tree_named_for_the_study(s: Sandbox) -> tuple[int, str]:
    """The checkout's name says what the take is, and the agent is shown its working directory."""
    s.control(_th(s, "TheRunTreeCarriesNothing"))
    _edit(s.study / "drive.py",
          "return Path(tempfile.gettempdir()).resolve() / neutral_name(session_id)",
          "return Path(tempfile.gettempdir()).resolve() / ('gap-study-' + neutral_name(session_id))")
    return s.run(_th(s, "TheRunTreeCarriesNothing")), "test_harness.py TheRunTreeCarriesNothing"


def m_study_names_dropped_from_the_leak_list(s: Sandbox) -> tuple[int, str]:
    """Review 11, F2: a leak list that cannot name the study reports clean on a leaked walk."""
    s.control(_th(s, "TheLeakCheckReadsEveryChannel"))
    p = s.study / "prereg-draft.json"
    d = json.loads(p.read_text())
    d["leak_words"] = [w for w in d["leak_words"]
                       if w not in ("gap-study", "gap study", "prereg", "pre-registration",
                                    "pre-registered")]
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    return (s.run(_th(s, "TheLeakCheckReadsEveryChannel")),
            "test_harness.py TheLeakCheckReadsEveryChannel")


def m_published_walk_carries_the_email(s: Sandbox) -> tuple[int, str]:
    """Ruling 10: a published transcript that still carries the account's email address field."""
    p = s.study / "walks" / "number-fidelity" / "2" / "transcript.jsonl"
    guard = [str(s.study / "check_take.py"), str(p), "--task", "number-fidelity", "--half", "control",
             "--walk"]
    s.control(guard)
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
    return s.run(guard), "check_take.py on a published walk carrying the email field"


def m_carried_line_edited(s: Sandbox) -> tuple[int, str]:
    """A carried operator line edited in the draft: the projection is no longer script()."""
    s.control(_th(s, "CarriedScriptIsTheFirstStudys"))
    p = s.study / "prereg-draft.json"
    d = json.loads(p.read_text())
    step = next(t for t in d["tasks"] if t["id"] == "confounded-design")["positive"]["operator_script"][1]
    if step["line"] != "05":
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    step["line"] = "5"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return (s.run(_th(s, "CarriedScriptIsTheFirstStudys")),
            "test_harness.py CarriedScriptIsTheFirstStudys")


def m_recovery_read_as_improvisation(s: Sandbox) -> tuple[int, str]:
    """The checker with its recovery allowance removed: the take a recovery rescued is refused."""
    s.control(_th(s, "TheCheckerAdmitsOnlyThePreRegisteredScript"))
    _edit(s.study / "check_take.py", '        if rec:\n            at_most = int(rec.get("at_most", 1))',
          '        if False:\n            at_most = int(rec.get("at_most", 1))')
    return (s.run(_th(s, "TheCheckerAdmitsOnlyThePreRegisteredScript")),
            "test_harness.py TheCheckerAdmitsOnlyThePreRegisteredScript")


def m_marker_compared_loosely(s: Sandbox) -> tuple[int, str]:
    """The driver comparing markers case-insensitively: a lowercase fragment would hold."""
    s.control(_th(s, "TheThenStepAndComparisonAreData"))
    _edit(s.study / "drive.py", "return True if marker is None else marker in said",
          "return True if marker is None else marker.lower() in said.lower()")
    return (s.run(_th(s, "TheThenStepAndComparisonAreData")),
            "test_harness.py TheThenStepAndComparisonAreData")


def m_carried_marker_not_template_bytes(s: Sandbox) -> tuple[int, str]:
    """Ruling 12: the first study's `stage 01` put back as a carried marker."""
    s.control(_th(s, "MarkersAreTemplateBytes"))
    p = s.study / "prereg-draft.json"
    d = json.loads(p.read_text())
    step = next(t for t in d["tasks"] if t["id"] == "confounded-design")["positive"]["operator_script"][3]
    step["marker"] = step["first_study_marker"]
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return s.run(_th(s, "MarkersAreTemplateBytes")), "test_harness.py MarkersAreTemplateBytes"


def m_notification_read_as_an_operator_line(s: Sandbox) -> tuple[int, str]:
    """Ruling 12: the checker no longer recognising a harness-delivered record."""
    s.control(_th(s, "TheCheckerReadsOperatorTurnsNotHarnessRecords"))
    _edit(s.study / "check_take.py", "        elif kind in kinds:\n            harness.append(text)",
          "        elif False:\n            harness.append(text)")
    return (s.run(_th(s, "TheCheckerReadsOperatorTurnsNotHarnessRecords")),
            "test_harness.py TheCheckerReadsOperatorTurnsNotHarnessRecords")


def m_stop_at_a_held_marker_admitted(s: Sandbox) -> tuple[int, str]:
    """Ruling 12: a driver stop at a wait point the agent reached, passed by the checker."""
    s.control(_th(s, "AStoppedTakeIsCheckedUpToTheStop"))
    _edit(s.study / "check_take.py", "            if marker in after:", "            if False:")
    return (s.run(_th(s, "AStoppedTakeIsCheckedUpToTheStop")),
            "test_harness.py AStoppedTakeIsCheckedUpToTheStop")


def m_walk_message_left_out_of_its_suite(s: Sandbox) -> tuple[int, str]:
    """Requirement 1: a committed walk message missing from its task's case suite."""
    s.control(_th(s, "CaseSuites"))
    p = s.study / "cases" / "confounded-design.json"
    d = json.loads(p.read_text())
    before = len(d["cases"])
    d["cases"] = [c for c in d["cases"]
                  if not (c["walk"] == "confounded-design/1" and c["message_index"] == 6)]
    if len(d["cases"]) != before - 1:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return s.run(_th(s, "CaseSuites")), "test_harness.py CaseSuites"



def m_refused_checkout_left_behind(s: Sandbox) -> tuple[int, str]:
    """The first carried follow-up: the removal before the refusal taken out again."""
    s.control(_th(s, "TheRunTreeCarriesNothing"))
    _edit(s.study / "drive.py", "    if problems:\n        shutil.rmtree(tree, ignore_errors=True)\n",
          "    if problems:\n")
    return s.run(_th(s, "TheRunTreeCarriesNothing")), "test_harness.py TheRunTreeCarriesNothing"



def m_driver_outcome_the_reader_does_not_know(s: Sandbox) -> tuple[int, str]:
    """A reworded outcome the label reader does not recognise: a stopped take would read as complete."""
    s.control(_th(s, "TheDriverOutcomesMapToTheirLabels"))
    _edit(s.study / "drive.py", '"stopped — wait-point marker not held; graded as it stands"',
          '"stopped — marker missed"')
    return (s.run(_th(s, "TheDriverOutcomesMapToTheirLabels")),
            "test_harness.py TheDriverOutcomesMapToTheirLabels")


def m_recovery_failure_drops_its_step_row(s: Sandbox) -> tuple[int, str]:
    """The step row removed again from the timed-out recovery branch."""
    s.control(_th(s, "TheDriverLoopRecordsEveryTurnItEnds"))
    p = s.study / "drive.py"
    text = p.read_text()
    a = text.index("            if code2 == 124:\n")
    b = text.index('                ledger["outcome"] = "timed-out"\n', a)
    if 'ledger["turns"].insert(' not in text[a:b]:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    p.write_text(text[:a] + "            if code2 == 124:\n" + text[b:])
    return (s.run(_th(s, "TheDriverLoopRecordsEveryTurnItEnds")),
            "test_harness.py TheDriverLoopRecordsEveryTurnItEnds")


def m_verdict_read_with_a_default(s: Sandbox) -> tuple[int, str]:
    """The analysis reaching for the verdict field with a default instead of indexing it."""
    s.control(_th(s, "Analysis"))
    p = s.study / "analyse.py"
    _edit(p, 'holds and res["layer"]["observed_for_probed_behaviour"] == "silent"),',
          'holds and res["layer"].get("observed_for_probed_behaviour") == "silent"),')
    _edit(p, '"layer": res["layer"]["observed_for_probed_behaviour"],',
          '"layer": res["layer"].get("observed_for_probed_behaviour"),')
    return s.run(_th(s, "Analysis")), "test_harness.py Analysis"



def m_rate_guard_unbounded(s: Sandbox) -> tuple[int, str]:
    """Ruling 13: the slash pattern without its word boundaries, which walk 2's ledger tripped."""
    s.control(_th(s, "TheLanguageGuardIsWordBounded"))
    _edit(s.study / "lint_language.py", r'r"\b\d+\s*/\s*\d+\b"', r'r"\d+\s*/\s*\d+"')
    return (s.run(_th(s, "TheLanguageGuardIsWordBounded")),
            "test_harness.py TheLanguageGuardIsWordBounded")


def m_turn_five_marker_back_to_the_sentence(s: Sandbox) -> tuple[int, str]:
    """Ruling 13: the carried turn-5 marker returned to the T4 sentence walk 2's agent reworded."""
    s.control(_th(s, "TheMarkersHoldOnRealReplies"))
    p = s.study / "prereg-draft.json"
    d = json.loads(p.read_text())
    for half in ("positive", "control"):
        step = next(x for x in next(t for t in d["tasks"] if t["id"] == "confounded-design")[half]["operator_script"]
                    if x["n"] == 5)
        step["marker"] = "Say when you are ready and I will start the bioinformatics for"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return s.run(_th(s, "TheMarkersHoldOnRealReplies")), "test_harness.py TheMarkersHoldOnRealReplies"



def m_slot_not_released_by_a_rehearsal(s: Sandbox) -> tuple[int, str]:
    """Slice 42: every earlier row holds its slot, so a rehearsed slot can never be retried."""
    s.control(_th(s, "TheTakeLifecycle"))
    _edit(s.study / "takes.py", '    live = [i for i in slot if outcome(i) not in ("rehearsal", "pause")]\n',
          "    live = slot\n")
    return s.run(_th(s, "TheTakeLifecycle")), "test_harness.py TheTakeLifecycle"


def m_rehearsal_cap_unenforced(s: Sandbox) -> tuple[int, str]:
    s.control(_th(s, "TheTakeLifecycle"))
    _edit(s.study / "takes.py", '    if len(rehearsed) >= int(pre["rehearsal_cap"]):\n', "    if False:\n")
    return s.run(_th(s, "TheTakeLifecycle")), "test_harness.py TheTakeLifecycle"


def m_untagged_refusal_routed(s: Sandbox) -> tuple[int, str]:
    """Slice 42: a refusal with no reason id routed anyway, as a rehearsal nobody can explain."""
    s.control(_th(s, "TheAttemptIsRoutedByRule"))
    _edit(s.study / "drive.py", "        if len(tagged) != len(problems):\n", "        if False:\n")
    return s.run(_th(s, "TheAttemptIsRoutedByRule")), "test_harness.py TheAttemptIsRoutedByRule"


def m_walk_rehearsal_counted_against_a_cell(s: Sandbox) -> tuple[int, str]:
    s.control(_th(s, "TheRunnerEnumeratesByLedger"))
    _edit(s.study / "run.py", '        if row.get("kind") != "take":\n            continue\n', "")
    return s.run(_th(s, "TheRunnerEnumeratesByLedger")), "test_harness.py TheRunnerEnumeratesByLedger"


def m_refusal_reason_unlisted(s: Sandbox) -> tuple[int, str]:
    """Slice 42: a reason the checker gives, dropped from the pre-registered list."""
    s.control(_th(s, "TheRefusalReasonsArePreRegistered"))
    p = s.study / "prereg-draft.json"
    d = json.loads(p.read_text())
    if d["rehearsal_reasons"].pop("stop-at-held-marker", None) is None:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return (s.run(_th(s, "TheRefusalReasonsArePreRegistered")),
            "test_harness.py TheRefusalReasonsArePreRegistered")


MUTATIONS = [
    ("an edited contract quote", m_edited_contract_quote, "objects"),
    ("an emptied quote table", m_emptied_quote_table, "objects"),
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
    ("a marker compared loosely", m_marker_compared_loosely, False),
    ("a carried marker that is not template bytes", m_carried_marker_not_template_bytes, False),
    ("a harness notification read as an operator line", m_notification_read_as_an_operator_line, False),
    ("a stop at a held marker admitted", m_stop_at_a_held_marker_admitted, False),
    ("a walk message left out of its suite", m_walk_message_left_out_of_its_suite, False),
    ("a refused checkout left behind", m_refused_checkout_left_behind, False),
    ("a driver outcome the label reader does not know", m_driver_outcome_the_reader_does_not_know, False),
    ("a failed recovery that drops its step row", m_recovery_failure_drops_its_step_row, True),
    ("the verdict field read with a default", m_verdict_read_with_a_default, False),
    ("the rate guard without its word boundaries", m_rate_guard_unbounded, False),
    ("the turn-5 marker back to the reworded sentence", m_turn_five_marker_back_to_the_sentence, False),
    ("a rehearsed slot that is never released", m_slot_not_released_by_a_rehearsal, False),
    ("the rehearsal cap unenforced", m_rehearsal_cap_unenforced, False),
    ("a refusal with no reason id routed", m_untagged_refusal_routed, False),
    ("a walk rehearsal counted against a take cell", m_walk_rehearsal_counted_against_a_cell, False),
    ("a refusal reason dropped from the list", m_refusal_reason_unlisted, False),
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
    controlled = 0
    for name, fn, needs_git in MUTATIONS:
        s = Sandbox(git=needs_git)
        try:
            code, guard = fn(s)
        except Exception as exc:  # a mutation that cannot even run is a failure of this file
            code, guard = 0, f"raised {exc!r}"
        finally:
            was_controlled = s.controlled
            s.close()
        ok = code != 0
        controlled += bool(ok and was_controlled)
        mark = "ctl" if was_controlled else "   "
        print(f"  {'red ' if ok else 'GREEN'} {mark} exit {code:<3} {name:48} {guard}")
        if not ok:
            failures.append(name)
    print(f"\n{controlled} of {len(MUTATIONS)} guards were watched green unmutated before going red "
          f"(`ctl`). The rest run a command that writes, or a guard with no unmutated form.")

    print(f"\n{len(NOT_APPLICABLE)} mutation(s) NOT APPLICABLE yet, listed rather than dropped:")
    for name, why in NOT_APPLICABLE:
        print(f"  n/a   {name:44} {why}")

    if failures:
        print(f"\n{len(failures)} guard(s) did NOT go red: {failures}")
        print("A guard that cannot fail is not protecting anything.")
        return 1
    print(f"\nevery one of the {len(MUTATIONS)} guards went red when broken")
    return 0
