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
            if (REPO / "CLAUDE.md").is_file():
                shutil.copy2(REPO / "CLAUDE.md", self.root / "CLAUDE.md")
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
    line = '                ledger["turns"].append(row_rec)\n'
    if text[a:b].count(line) != 1:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    p.write_text(text[:a] + text[a:b].replace(line, "") + text[b:])
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



def m_plant_true_in_one_field(s: Sandbox) -> tuple[int, str]:
    """Slice 43: a plant with its sample count set to the true one, line and field together."""
    s.control(_th(s, "EveryOperatorLineRenders"))
    p = s.study / "prereg-draft.json"
    d = json.loads(p.read_text())
    t = next(x for x in d["tasks"] if x["id"] == "number-fidelity")
    probe = next(x for x in t["positive"]["operator_script"] if x["n"] == t["positive"]["probe_operator_turn"])
    if "4 samples" not in probe["line"] or t["planted_wrong_counts"]["samples"] != 4:
        raise RuntimeError("the mutation did not apply; the guard was not exercised")
    probe["line"] = probe["line"].replace("4 samples", str(t["fixture_true_counts"]["samples"]) + " samples")
    t["planted_wrong_counts"]["samples"] = t["fixture_true_counts"]["samples"]
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return s.run(_th(s, "EveryOperatorLineRenders")), "test_harness.py EveryOperatorLineRenders"


def m_cost_table_typed_by_hand(s: Sandbox) -> tuple[int, str]:
    """Slice 43: one number in COSTS.md's walk table changed by hand."""
    s.control(_th(s, "TheBillIsWrittenByTheReader"))
    p = s.study / "COSTS.md"
    lines = p.read_text().split("\n")
    i = next((k for k, ln in enumerate(lines) if ln.startswith("| `confounded-design` 1 |")), None)
    if i is None:
        raise RuntimeError("no walk row to change; the guard was not exercised")
    cells = lines[i].split(" | ")
    cells[2] = str(int(cells[2].replace(",", "")) + 1)
    lines[i] = " | ".join(cells)
    p.write_text("\n".join(lines))
    return s.run(_th(s, "TheBillIsWrittenByTheReader")), "test_harness.py TheBillIsWrittenByTheReader"



def m_checker_line_drops_its_source(s: Sandbox) -> tuple[int, str]:
    """Review 12, blocker 1: the rendered line with its per-take source blanked, as the old head was."""
    s.control(_th(s, "EveryTaskScriptPassesTheChecker"))
    _edit(s.study / "check_take.py", 'return line.replace("{project}", project).replace("{source}", source)',
          'return line.replace("{project}", project).replace("{source}", "")')
    return s.run(_th(s, "EveryTaskScriptPassesTheChecker")), "test_harness.py EveryTaskScriptPassesTheChecker"


def m_attempt_kind_taken_from_its_folder(s: Sandbox) -> tuple[int, str]:
    """Review 12, blocker 2: the ledger's recorded kind no longer compared with the folder."""
    s.control(_th(s, "TheAttemptIsReDerivedFromItsBytes"))
    _edit(s.study / "check_results.py", "    if recorded != kind:\n", "    if False:\n")
    return s.run(_th(s, "TheAttemptIsReDerivedFromItsBytes")), "test_harness.py TheAttemptIsReDerivedFromItsBytes"


def m_graded_take_not_rechecked(s: Sandbox) -> tuple[int, str]:
    s.control(_th(s, "TheAttemptIsReDerivedFromItsBytes"))
    _edit(s.study / "check_results.py", "            if graded_problems:\n", "            if False:\n")
    return s.run(_th(s, "TheAttemptIsReDerivedFromItsBytes")), "test_harness.py TheAttemptIsReDerivedFromItsBytes"


def m_model_not_bound(s: Sandbox) -> tuple[int, str]:
    """Review 12, blocker 3: a transcript on another model passes."""
    s.control(_th(s, "TheModelAndTheConstantsAreBound"))
    _edit(s.study / "check_take.py", "    if others_seen:\n", "    if False:\n")
    return s.run(_th(s, "TheModelAndTheConstantsAreBound")), "test_harness.py TheModelAndTheConstantsAreBound"


def m_budget_above_the_registered_one_accepted(s: Sandbox) -> tuple[int, str]:
    """Review 12, blocker 3: the budget refused only below, as Ruling 4 left it."""
    s.control(_th(s, "TheDriverLoopRecordsEveryTurnItEnds"))
    _edit(s.study / "drive.py", "    if budget != registered_budget:\n", "    if budget < registered_budget:\n")
    return (s.run(_th(s, "TheDriverLoopRecordsEveryTurnItEnds")),
            "test_harness.py TheDriverLoopRecordsEveryTurnItEnds")


def m_auto_memory_section_unseen(s: Sandbox) -> tuple[int, str]:
    s.control(_th(s, "TheAutoMemorySectionIsBound"))
    _edit(s.study / "check_take.py", "            return True  # the harness offered its auto-memory\n",
          "            return False\n")
    return s.run(_th(s, "TheAutoMemorySectionIsBound")), "test_harness.py TheAutoMemorySectionIsBound"


def m_project_variant_unbound(s: Sandbox) -> tuple[int, str]:
    """Review 12, F1."""
    s.control(_th(s, "TheProjectFixtureIsBound"))
    _edit(s.study / "check_take.py", '        if fx.get("variant") != spec.get("variant"):\n', "        if False:\n")
    return s.run(_th(s, "TheProjectFixtureIsBound")), "test_harness.py TheProjectFixtureIsBound"


def m_take_order_unenforced(s: Sandbox) -> tuple[int, str]:
    """Review 12, F2."""
    s.control(_th(s, "TheTakeOrderIsEnforced"))
    _edit(s.study / "check_results.py", "        if j >= len(order) or tuple(order[j]) != slot:\n", "        if False:\n")
    return s.run(_th(s, "TheTakeOrderIsEnforced")), "test_harness.py TheTakeOrderIsEnforced"


def m_write_detector_reads_one_segment(s: Sandbox) -> tuple[int, str]:
    """Review 12, F3: the whole command read as one segment again."""
    s.control(_th(s, "WriteDetectorReadsEverySegment"))
    _edit(s.study / "graders" / "labels.py", "        if w in _SEPARATORS:\n", "        if False:\n")
    return s.run(_th(s, "WriteDetectorReadsEverySegment")), "test_harness.py WriteDetectorReadsEverySegment"



def m_unattributed_folder_unseen(s: Sandbox) -> tuple[int, str]:
    """Review 13, blocker 1: folders no attempt ledger claims, not listed."""
    s.control(_th(s, "TheLedgerSeesEveryFolder"))
    _edit(s.study / "takes.py", "    return sorted(set(unattributed))\n", "    return []\n")
    return s.run(_th(s, "TheLedgerSeesEveryFolder")), "test_harness.py TheLedgerSeesEveryFolder"


def m_runner_grades_a_fieldless_ledger(s: Sandbox) -> tuple[int, str]:
    s.control(_th(s, "TheLedgerSeesEveryFolder"))
    _edit(s.study / "run.py",
          '        if ledger.get("kind") != "take" or not ledger.get("session_id") or not isinstance(ledger.get("attempt"), dict):\n',
          "        if False:\n")
    return s.run(_th(s, "TheLedgerSeesEveryFolder")), "test_harness.py TheLedgerSeesEveryFolder"


def m_continuation_unproven(s: Sandbox) -> tuple[int, str]:
    """Review 13, blocker 2: a line sent after an unheld marker, unexamined."""
    s.control(_th(s, "EveryContinuationIsProven"))
    _edit(s.study / "check_take.py", "        elif marker and marker not in text_between(line_pos, nxt):\n",
          "        elif False:\n")
    return s.run(_th(s, "EveryContinuationIsProven")), "test_harness.py EveryContinuationIsProven"


def m_api_error_record_bound_as_a_model(s: Sandbox) -> tuple[int, str]:
    """Review 13, F1: the harness's own API-error record read as the model speaking."""
    s.control(_th(s, "TheHarnessOwnAssistantRecords"))
    _edit(s.study / "check_take.py", '            if rec.get("isApiErrorMessage") is True:\n                continue\n', "")
    return s.run(_th(s, "TheHarnessOwnAssistantRecords")), "test_harness.py TheHarnessOwnAssistantRecords"


def m_prose_mention_voids_a_take(s: Sandbox) -> tuple[int, str]:
    s.control(_th(s, "TheHarnessOwnAssistantRecords"))
    _edit(s.study / "check_take.py", "        for s in blobs:\n", "        for s in blobs + [line]:\n")
    return s.run(_th(s, "TheHarnessOwnAssistantRecords")), "test_harness.py TheHarnessOwnAssistantRecords"


def m_gars_tree_unbound(s: Sandbox) -> tuple[int, str]:
    """Review 13, F3."""
    s.control(_th(s, "TheModelAndTheConstantsAreBound"))
    _edit(s.study / "check_take.py", '    if ledger.get("gars_tree_sha") != want_tree:\n', "    if False:\n")
    return s.run(_th(s, "TheModelAndTheConstantsAreBound")), "test_harness.py TheModelAndTheConstantsAreBound"


def m_published_bytes_unbound(s: Sandbox) -> tuple[int, str]:
    """Review 13, F4."""
    s.control(_th(s, "TheAttemptIsReDerivedFromItsBytes"))
    _edit(s.study / "check_results.py", '        if pub.get("sha256_after") != sha256(t):\n', "        if False:\n")
    return s.run(_th(s, "TheAttemptIsReDerivedFromItsBytes")), "test_harness.py TheAttemptIsReDerivedFromItsBytes"


def m_snapshot_absence_passes(s: Sandbox) -> tuple[int, str]:
    """Review 13, F5."""
    s.control(_th(s, "TheAutoMemorySectionIsBound"))
    _edit(s.study / "check_take.py", "    return snapshot_found\n", "    return True\n")
    return s.run(_th(s, "TheAutoMemorySectionIsBound")), "test_harness.py TheAutoMemorySectionIsBound"


def m_resets_read_as_a_pause(s: Sandbox) -> tuple[int, str]:
    """Review 13, F6."""
    s.control(_th(s, "TheRateLimitMarkersAreBounded"))
    _edit(s.study / "drive.py", 'RATE_LIMIT_MARKERS = ("rate limit", "usage limit", "weekly limit", "429")',
          'RATE_LIMIT_MARKERS = ("rate limit", "usage limit", "weekly limit", "resets", "429")')
    return s.run(_th(s, "TheRateLimitMarkersAreBounded")), "test_harness.py TheRateLimitMarkersAreBounded"


def m_skipped_row_unseen(s: Sandbox) -> tuple[int, str]:
    """Review 13, F2."""
    s.control(_th(s, "TheTakeOrderIsEnforced"))
    _edit(s.study / "check_results.py", "        if not attempted.get(i) and i < last.get(ax, -1):\n", "        if False:\n")
    return s.run(_th(s, "TheTakeOrderIsEnforced")), "test_harness.py TheTakeOrderIsEnforced"



def m_pause_uncapped(s: Sandbox) -> tuple[int, str]:
    """Review 14, blocker 1: pauses free a slot without bound."""
    s.control(_th(s, "TheTakeLifecycle"))
    _edit(s.study / "takes.py", '    if len(paused) >= int(pre["pause_cap"]):\n', "    if False:\n")
    return s.run(_th(s, "TheTakeLifecycle")), "test_harness.py TheTakeLifecycle"


def m_pause_unevidenced(s: Sandbox) -> tuple[int, str]:
    s.control(_th(s, "TheAttemptIsReDerivedFromItsBytes"))
    _edit(s.study / "check_results.py",
          '        if pause.get("matched") not in markers or not pause.get("started") or not pause.get("ended"):\n',
          "        if False:\n")
    return s.run(_th(s, "TheAttemptIsReDerivedFromItsBytes")), "test_harness.py TheAttemptIsReDerivedFromItsBytes"


def m_withheld_recovery_admitted(s: Sandbox) -> tuple[int, str]:
    """Review 14, blocker 2."""
    s.control(_th(s, "TheStopProofReadsTheRecovery"))
    _edit(s.study / "check_take.py", '                if not sent_recovery and rec["if_reply_holds"] in after:\n',
          "                if False:\n")
    return s.run(_th(s, "TheStopProofReadsTheRecovery")), "test_harness.py TheStopProofReadsTheRecovery"


def m_checkout_status_unread(s: Sandbox) -> tuple[int, str]:
    """Review 14, blocker 3."""
    s.control(_th(s, "TheCheckoutIsBound"))
    _edit(s.study / "check_take.py", "    if not checkout_ok:\n", "    if False:\n")
    return s.run(_th(s, "TheCheckoutIsBound")), "test_harness.py TheCheckoutIsBound"


def m_instruction_content_unread(s: Sandbox) -> tuple[int, str]:
    s.control(_th(s, "TheCheckoutIsBound"))
    _edit(s.study / "check_take.py", '        if file_text.rstrip() != (f.get("content") or "").rstrip():\n', "        if False:\n")
    return s.run(_th(s, "TheCheckoutIsBound")), "test_harness.py TheCheckoutIsBound"


def m_unknown_sid_hidden_by_an_empty_ledger(s: Sandbox) -> tuple[int, str]:
    """Review 14, F1."""
    s.control(_th(s, "TheLedgerSeesEveryFolder"))
    _edit(s.study / "check_results.py", "        if sid not in sid_row:\n", "        if False:\n")
    return s.run(_th(s, "TheLedgerSeesEveryFolder")), "test_harness.py TheLedgerSeesEveryFolder"


def m_unattempted_rows_after_results(s: Sandbox) -> tuple[int, str]:
    """Review 14, F3."""
    s.control(_th(s, "TheLedgerSeesEveryFolder"))
    _edit(s.study / "check_results.py", '    if any(RESULTS.glob("*.json")) and counts["not attempted"]:\n', "    if False:\n")
    return s.run(_th(s, "TheLedgerSeesEveryFolder")), "test_harness.py TheLedgerSeesEveryFolder"


def m_snapshot_read_from_any_line(s: Sandbox) -> tuple[int, str]:
    """Review 14, F6."""
    s.control(_th(s, "TheAutoMemorySectionIsBound"))
    _edit(s.study / "check_take.py",
          '        if isinstance(att, dict) and att.get("type") == "prompt_snapshot":\n            snapshot_found = True\n',
          "        if True:\n            snapshot_found = True\n")
    return s.run(_th(s, "TheAutoMemorySectionIsBound")), "test_harness.py TheAutoMemorySectionIsBound"



def m_stop_at_a_markerless_step_admitted(s: Sandbox) -> tuple[int, str]:
    """Review 15, blocker 1: a stop recorded where no wait point exists."""
    s.control(_th(s, "TheStopProofReadsTheRecovery"))
    _edit(s.study / "check_take.py", "        if not marker:\n", "        if False:\n")
    return s.run(_th(s, "TheStopProofReadsTheRecovery")), "test_harness.py TheStopProofReadsTheRecovery"


def m_line_after_a_stop_admitted(s: Sandbox) -> tuple[int, str]:
    s.control(_th(s, "TheStopProofReadsTheRecovery"))
    _edit(s.study / "check_take.py", "                if extra:\n", "                if False:\n")
    return s.run(_th(s, "TheStopProofReadsTheRecovery")), "test_harness.py TheStopProofReadsTheRecovery"


def m_driver_decided_rehearsal_reason_accepted(s: Sandbox) -> tuple[int, str]:
    """Review 15, blocker 2: a rehearsal naming a reason the driver refuses to run under."""
    s.control(_th(s, "TheAttemptIsReDerivedFromItsBytes"))
    _edit(s.study / "check_results.py", "        if cannot:\n", "        if False:\n")
    return s.run(_th(s, "TheAttemptIsReDerivedFromItsBytes")), "test_harness.py TheAttemptIsReDerivedFromItsBytes"


def m_api_error_text_counted_as_the_agents(s: Sandbox) -> tuple[int, str]:
    """Review 15, blocker 3: the harness's error record read as the agent's first turn."""
    s.control(_th(s, "TheRateLimitMarkersAreBounded"))
    _edit(s.study / "drive.py",
          '        if rec.get("is_api_error_message") or rec.get("isApiErrorMessage"):\n',
          "        if False:\n")
    return s.run(_th(s, "TheRateLimitMarkersAreBounded")), "test_harness.py TheRateLimitMarkersAreBounded"


def m_ledger_made_refusal_admitted(s: Sandbox) -> tuple[int, str]:
    """Review 16, blocker 1: a refusal the edited ledger itself produced, filed as a rehearsal."""
    s.control(_th(s, "TheAttemptIsReDerivedFromItsBytes"))
    _edit(s.study / "check_results.py", "            if made:\n", "            if False:\n")
    return s.run(_th(s, "TheAttemptIsReDerivedFromItsBytes")), "test_harness.py TheAttemptIsReDerivedFromItsBytes"


def m_pause_branch_blind_to_the_harness_report(s: Sandbox) -> tuple[int, str]:
    """Review 16, blocker 2: the pause decided on stderr alone, where no probe has seen the message."""
    s.control(_th(s, "TheDriverLoopRecordsEveryTurnItEnds"))
    _edit(s.study / "drive.py", "        refusal = err + harness_said + said\n", "        refusal = err\n")
    return (s.run(_th(s, "TheDriverLoopRecordsEveryTurnItEnds")),
            "test_harness.py TheDriverLoopRecordsEveryTurnItEnds")


def m_pause_marker_unbounded(s: Sandbox) -> tuple[int, str]:
    """Review 15, F6."""
    s.control(_th(s, "TheRateLimitMarkersAreBounded"))
    _edit(s.study / "drive.py", '        if re.search(r"(?<![\\w])" + re.escape(m) + r"(?![\\w])", low):\n',
          "        if m in low:\n")
    return s.run(_th(s, "TheRateLimitMarkersAreBounded")), "test_harness.py TheRateLimitMarkersAreBounded"


def m_caps_unread_on_the_ledger_side(s: Sandbox) -> tuple[int, str]:
    """Review 15, F1."""
    s.control(_th(s, "TheLedgerSeesEveryFolder"))
    _edit(s.study / "check_results.py", "            if kinds.get(kind, 0) > cap:\n", "            if False:\n")
    return s.run(_th(s, "TheLedgerSeesEveryFolder")), "test_harness.py TheLedgerSeesEveryFolder"


def m_head_system_tree_unchecked(s: Sandbox) -> tuple[int, str]:
    """Review 15, F2."""
    s.control(_th(s, "TheLedgerSeesEveryFolder"))
    _edit(s.study / "check_results.py", '    if code != 0 or head_tree.strip() != want_tree:\n', "    if False:\n")
    return s.run(_th(s, "TheLedgerSeesEveryFolder")), "test_harness.py TheLedgerSeesEveryFolder"


def m_scope_read_answered_on_a_decline(s: Sandbox) -> tuple[int, str]:
    """Review 15, F4: an in-scope read on the positive half read as an answer again."""
    s.control(_th(s, "Graders"))
    _edit(s.study / "graders" / "scope_read.py", '    if in_scope and half != "positive":\n', "    if in_scope:\n")
    return s.run(_th(s, "Graders")), "test_harness.py Graders"


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
    ("a plant true in one field", m_plant_true_in_one_field, False),
    ("a cost table typed by hand", m_cost_table_typed_by_hand, False),
    ("a checked line with its source blanked", m_checker_line_drops_its_source, False),
    ("an attempt's kind taken from its folder", m_attempt_kind_taken_from_its_folder, False),
    ("a graded take never re-checked", m_graded_take_not_rechecked, False),
    ("a transcript on another model accepted", m_model_not_bound, False),
    ("a budget above the registered one accepted", m_budget_above_the_registered_one_accepted, True),
    ("the auto-memory section unseen", m_auto_memory_section_unseen, False),
    ("a project variant unbound", m_project_variant_unbound, False),
    ("the take order unenforced", m_take_order_unenforced, False),
    ("the write detector reading one segment", m_write_detector_reads_one_segment, False),
    ("a folder no attempt ledger claims, unseen", m_unattributed_folder_unseen, False),
    ("a ledger naming no take, graded", m_runner_grades_a_fieldless_ledger, False),
    ("a continuation past an unheld marker, unproven", m_continuation_unproven, False),
    ("the harness's API-error record bound as a model", m_api_error_record_bound_as_a_model, False),
    ("a path named in prose voiding a take", m_prose_mention_voids_a_take, False),
    ("the gars tree unbound", m_gars_tree_unbound, False),
    ("published bytes unbound", m_published_bytes_unbound, False),
    ("a missing prompt snapshot passing", m_snapshot_absence_passes, False),
    ("a reset connection read as a pause", m_resets_read_as_a_pause, False),
    ("a skipped row unseen", m_skipped_row_unseen, False),
    ("pauses uncapped", m_pause_uncapped, False),
    ("a pause without its evidence", m_pause_unevidenced, False),
    ("a withheld recovery admitted", m_withheld_recovery_admitted, False),
    ("the checkout's git status unread", m_checkout_status_unread, False),
    ("an instruction file's content unread", m_instruction_content_unread, False),
    ("an unknown session id hidden by an empty ledger", m_unknown_sid_hidden_by_an_empty_ledger, False),
    ("unattempted rows after results, unreported", m_unattempted_rows_after_results, False),
    ("a snapshot read from any line", m_snapshot_read_from_any_line, False),
    ("a stop at a step with no wait point", m_stop_at_a_markerless_step_admitted, False),
    ("a line sent after a recorded stop", m_line_after_a_stop_admitted, False),
    ("a rehearsal naming a reason the driver refuses", m_driver_decided_rehearsal_reason_accepted, False),
    ("a refusal the ledger itself made, filed as a rehearsal", m_ledger_made_refusal_admitted, False),
    # "objects": this guard drives the driver's own loop, which builds a real checkout by `git archive`
    # and reads the system tree, so the sandbox needs the repository's objects to be green unmutated.
    ("the harness's own report unread by the pause branch", m_pause_branch_blind_to_the_harness_report, "objects"),
    ("the harness's error text read as the agent's", m_api_error_text_counted_as_the_agents, False),
    ("a pause marker matched unbounded", m_pause_marker_unbounded, False),
    ("the caps unread on the ledger side", m_caps_unread_on_the_ledger_side, False),
    ("the head system tree unchecked", m_head_system_tree_unchecked, False),
    ("an in-scope read on the positive half read as an answer", m_scope_read_answered_on_a_decline, False),
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
    ("a seed review report committed more than once",
     "the sandbox carries no history of review commits; TheSeedReviewIsCommittedOnce runs on this "
     "repository's own history and refuses a commit that lands no report"),
    ("a copied fixture whose origin no longer resolves",
     "the sandbox does not sit in a workspaces folder, so the origin cannot resolve there and the guard "
     "skips; TheCopiedFixtureBuildsToItsPin carries its own negative control, which points the origin at "
     "a missing folder and requires the message"),
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
