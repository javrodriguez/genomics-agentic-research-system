#!/usr/bin/env python3
"""The publication job's text contract; no workflow or shell body is executed.

PL-5(a) assigns this file the workflow binding. --mutant NAME feeds altered
workflow text to the whole file. Mutations are armed in setUpModule only.
"""
from __future__ import annotations

import difflib
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import scratch_git

BASE = "89b54db4e34c18dcdde253c04179077a68f0888f"
KICKOFF = "ad88d14d82f8e88e5bf6253f03faadcfbbb242f4"
WORKFLOW = ".github/workflows/ci.yml"
JOB = "  gap-study-4:\n"
FROZEN = "evals/gap-study-4/prereg.json"
PRIVATE_MESSAGE = "holdout lives in the private aegis repo; checked locally at each freeze step"

# Plan 1013-1036, verbatim command spellings. The private command has a named
# deferral; --regrade remains the plan's command even while its flag is owed.
PLAN_COMMANDS = (
    "python3 evals/gap-study-4/lint_language.py evals/gap-study-4/",
    "python3 evals/gap-study-4/lint_pooling.py evals/gap-study-4/",
    "python3 -W ignore evals/gap-study-4/test_round4.py",
    "python3 evals/gap-study-4/copy_manifest.py --check",
    "python3 -W ignore evals/gap-study-4/tests/test_box_integration.py",
    "python3 -W ignore evals/gap-study-4/tests/test_pipeline.py",
    "python3 evals/gap-study-4/probes4.py --check",
    "python3 evals/gap-study-4/build_draft.py --check",
    "python3 evals/gap-study-4/leak_grep.py --check",
    "python3 evals/gap-study-4/holdout.py --check",
    "python3 evals/gap-study-4/review_kit/rounds.py --check",
    "python3 evals/gap-study-4/check_results.py",
    "python3 evals/gap-study-4/check_results.py --ledger",
    "python3 evals/gap-study-4/check_results.py --regrade",
)
AFTER = PLAN_COMMANDS[-3:] + (
    "python3 evals/gap-study-4/result.py --check",
    "python3 evals/gap-study-4/completeness.py --check",
)
BEFORE = PLAN_COMMANDS[:9] + (PLAN_COMMANDS[10],)
COPY = PLAN_COMMANDS[3]
BOX = PLAN_COMMANDS[4]
BOX_OWNER = "      # CP2 owns tests/test_box_integration.py; omitted until it exists\n"
BOX_RULING = "      # under glitch-f3's section 10 box-integration ruling.\n"
BOX_DEFERRED = BOX_OWNER + BOX_RULING
BOX_STEP = (
    "      - name: Box integration\n"
    "        # Binds the integrated box interface supplied by CP2.\n"
    f"        run: {BOX}\n"
)
ZERO_RULE = (
    "THE ZERO RULE. Each step below either grades a countable number of items or says it graded none. "
    "Before the freeze there are no takes and no result, so the two steps that need them report "
    "`not applicable — not frozen` rather than a pass. AFTER the freeze, a step that grades zero items "
    "is a FAILURE: a green that measured nothing is the defect this study spent a round learning about."
)
COUNT_COMMAND = (
    'python3 -c "import sys; sys.path.insert(0, \'evals/gap-study-4\'); import stats; '
    'n = len(stats.load_results()); print(f\'records available: {n}\'); '
    'raise SystemExit(0 if n else \'FAIL: frozen and 0 records\')"'
)
SELECTED = None
RAW = CURRENT = BASE_TEXT = INTRODUCED = None
CURRENT_BOX_PRESENT = None


def git(repo, *args):
    got = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if got.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {got.stderr.strip()}")
    return got.stdout


def history(repo):
    if git(repo, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise AssertionError("full history is required")
    baseline = git(repo, "show", f"{BASE}:{WORKFLOW}")
    added = git(repo, "log", "--diff-filter=A", "--format=%H", "--",
                "evals/gap-study-4/study.py").splitlines()
    if added != [KICKOFF]:
        raise AssertionError(f"unexpected introducing commit: {added!r}")
    return baseline, added[0]


def job_block(text):
    if text.count(JOB) != 1:
        return None
    start = text.index(JOB)
    following = re.search(r"^  [A-Za-z0-9_-]+:\s*$", text[start + len(JOB):], re.M)
    end = start + len(JOB) + following.start() if following else len(text)
    return text[start:end]


def steps(block):
    result = []
    pattern = r"^      - name: ([^\n]+)\n(.*?)(?=^      - (?:name|uses):|\Z)"
    for match in re.finditer(pattern, block, re.M | re.S):
        body = match[2]
        run = re.search(r"^        run: ([^\n]+)\n", body, re.M)
        if not run:
            result.append((match[1], body, ""))
        elif run[1] == "|":
            lines = body[run.end():].splitlines()
            literal = []
            for line in lines:
                if not line.strip():
                    continue
                if not line.startswith(" " * 10):
                    break
                literal.append(line[10:])
            result.append((match[1], body, "\n".join(literal)))
        else:
            result.append((match[1], body, run[1]))
    return result


def problems(text, baseline, introduced, *, box_present=None):
    """Clause ids and findings; a text reader, never a runner."""
    found = []

    def need(condition, clause):
        if not condition:
            found.append(clause)

    block = job_block(text)
    need(block is not None, "R35.count")
    if block is None:
        return found
    entries = steps(block)
    runs = [run for _, _, run in entries]
    comments = " ".join(re.findall(r"^\s*# ?(.*)$", block, re.M))
    need(re.findall(r"^    runs-on: (.+)$", block, re.M) == ["ubuntu-latest"], "R35.runner")
    need(re.findall(r"^      - uses: (.+)$", block, re.M) ==
         ["actions/checkout@v4", "actions/setup-python@v5"], "R35.actions")
    actions = dict(re.findall(r"^      - uses: ([^\n]+)\n(.*?)(?=^      - |\Z)", block, re.M | re.S))
    checkout = actions.get("actions/checkout@v4", "")
    setup = actions.get("actions/setup-python@v5", "")
    need('        with:\n' in checkout and '          fetch-depth: 0\n' in checkout, "R35.depth")
    need(all(word in comments for word in ("copy gate", "ledger", "history", "shallow clone")), "R35.history")
    need('        with:\n' in setup and '          python-version: "3.12"\n' in setup, "R35.python")
    env = ('    env:\n      GIT_CONFIG_COUNT: "2"\n'
           '      GIT_CONFIG_KEY_0: maintenance.auto\n      GIT_CONFIG_VALUE_0: "false"\n'
           '      GIT_CONFIG_KEY_1: gc.auto\n      GIT_CONFIG_VALUE_1: "0"\n')
    need(env in block, "R35.maintenance")
    need(entries and len({n for n, _, _ in entries}) == len(entries)
         and all(re.search(r"^        # \S", body, re.M) for _, body, _ in entries), "R35.comments")
    need(not re.search(r"^ {4,8}(?:if|continue-on-error|shell|working-directory):", block, re.M), "R35.runnable")
    need("plan 299" in comments and "intervals job" in comments and "stats.py" in comments
         and "CP8" in comments, "R35.scope")
    refs = re.findall(r"^\s*ref:\s*(.*)$", block, re.M)
    need(not refs or (len(refs) == 1 and re.fullmatch(r"[0-9a-fA-F]{40}", refs[0])), "R36.ref")
    need(refs == re.findall(r"^\s*ref:\s*(.*)$", checkout, re.M), "R36.location")
    need(all(word in comments for word in ("CP8", "publication commit", "done commit", "full sha", "Javier")),
         "R36.publication")

    # Removing only the new block must restore the whole old workflow byte for
    # byte. Thus triggers, siblings, and the intervals job remain bound too.
    need(text.replace(block, "", 1) == baseline, "R37.outside")
    need(text.split("jobs:\n", 1)[0] == baseline.split("jobs:\n", 1)[0], "R37.trigger")
    active = "\n".join(line for line in block.splitlines() if not line.lstrip().startswith("#"))
    need("secrets." not in active, "R37.secrets")
    need(not re.search(r"\bpermissions\s*:", active), "R37.permissions")
    for clause, pattern in (
        ("push", r"\bgit\s+push\b"), ("gh", r"\bgh\s+"),
        ("deploy", r"\bdeploy\b"), ("upload", r"\bupload(?:-artifact)?\b"),
        ("release", r"\brelease\b"), ("network", r"\b(?:curl|wget|fetch|clone|pip|npm)\b|https?://"),
    ):
        need(not re.search(pattern, "\n".join(runs), re.I), "R37." + clause)
    need(all(action in ("actions/checkout@v4", "actions/setup-python@v5")
             for action in re.findall(r"\buses:\s*(\S+)", active)), "R37.actions")

    if box_present is None:
        box_present = (HERE / "tests/test_box_integration.py").is_file()
    before = BEFORE if box_present else tuple(command for command in BEFORE if command != BOX)
    if not box_present:
        need(BOX_OWNER in block, "R38.box-owner")
        need(BOX_RULING in block, "R38.box-ruling")
        need(not any("test_box_integration.py" in run for run in runs), "R38.box-absent")
    expected = before + AFTER
    command_steps = {}
    for command in expected:
        matching = [(name, body, run) for name, body, run in entries
                    if command in [line.strip() for line in run.splitlines()]]
        need(len(matching) == 1, "R38.command:" + command)
        if len(matching) == 1:
            command_steps[command] = matching[0]
    need(len({entry[0] for entry in command_steps.values()}) == len(expected), "R38.separate")
    for command in before:
        if command != COPY and command in command_steps:
            need(command_steps[command][2] == command, "R38.before:" + command)
    for command in AFTER:
        if command in command_steps:
            lines = command_steps[command][2].splitlines()
            need(lines == [f"if [ -f {FROZEN} ]; then", "  " + COUNT_COMMAND, "  " + command,
                           "else", '  echo "not applicable — not frozen"', "fi"], "R38.after:" + command)

    private = [(name, body, run) for name, body, run in entries if PRIVATE_MESSAGE in run]
    need(len(private) == 1 and private[0][2] == f'echo "{PRIVATE_MESSAGE}"', "R39.message")
    need(not any("holdout.py" in run for run in runs), "R39.command")
    need(len(private) == 1 and "freeze_rehearsal.py" in private[0][1]
         and "at the freeze" in private[0][1], "R40.location")
    need(not any("freeze_rehearsal.py" in run for run in runs), "R40.execution")
    # R41's local binding is this entire file; the repository suite is owed to
    # the lane lead on athena, and must not be claimed as a command of this job.
    need(not any("tests/run_tests.py" in run for run in runs), "R41.local")

    if COPY in command_steps:
        run = command_steps[COPY][2]
        expected_copy = (
            f"if [ ! -f {FROZEN} ]; then\n"
            '  echo "copy gate commit: $(git rev-parse HEAD)"\n'
            f"  {COPY}\nelse\n"
            f"  freeze=$(git log --format=%H --reverse -- {FROZEN} | head -1)\n"
            '  test -n "$freeze"\n'
            '  copy_root="$RUNNER_TEMP/frozen-tree"\n'
            '  git worktree add --detach "$copy_root" "$freeze"\n'
            "  trap 'git worktree remove \"$copy_root\"' EXIT\n"
            '  echo "copy gate commit: $freeze"\n'
            '  python3 "$copy_root/evals/gap-study-4/copy_manifest.py" --check\nfi'
        )
        need(run == expected_copy, "R42.branches")
    else:
        need(False, "R42.branches")
    need(sum("copy_manifest.py" in line for entry in runs for line in entry.splitlines()) == 2,
         "R42.only")
    need(ZERO_RULE in comments, "R43.rule")
    for command in AFTER:
        if command in command_steps:
            run = command_steps[command][2]
            need(COUNT_COMMAND in run and run.index(COUNT_COMMAND) < run.index(command), "R43.count:" + command)
    # The additive check is read against the actual introducing commit, not a
    # branch name. Its shell body mirrors the sibling's shape exactly.
    need(introduced == KICKOFF, "R44.kickoff")
    addition = [run for name, _, run in entries if name == "Round 4 workflow diff is additive"]
    want_addition = (
        f"removed=$(git diff {introduced} HEAD --numstat -- .github/workflows/ \\\n"
        "          | awk '{s+=$2} END {print s+0}')\n"
        'echo "workflow lines removed since the kickoff: $removed"\n'
        'test "$removed" -eq 0'
    )
    need(addition == [want_addition], "R44.step")
    removed = sum(i2 - i1 for tag, i1, i2, _, _ in
                  difflib.SequenceMatcher(a=baseline.splitlines(), b=text.splitlines(), autojunk=False).get_opcodes()
                  if tag in ("delete", "replace"))
    need(removed == 0, "R44.additive")
    need(len(entries) == len(expected) + 2, "R38.total")
    return found


def replace_once(text, old, new):
    if old not in text:
        raise AssertionError(f"mutation site is missing: {old!r}")
    return text.replace(old, new, 1)


def mutations():
    """One named alteration for every bound clause, including every command."""
    edits = {
        "duplicate-job": ("R35.count", JOB, JOB + JOB),
        "runner": ("R35.runner", "    runs-on: ubuntu-latest", "    runs-on: macos-latest"),
        "checkout": ("R35.actions", "actions/checkout@v4", "actions/checkout@v3"),
        "python-action": ("R35.actions", "actions/setup-python@v5", "actions/setup-python@v4"),
        "depth": ("R35.depth", "fetch-depth: 0", "fetch-depth: 1"),
        "history-comment": ("R35.history", "shallow clone", "partial clone"),
        "python-version": ("R35.python", 'python-version: "3.12"', 'python-version: "3.13"'),
        "maintenance": ("R35.maintenance", 'GIT_CONFIG_VALUE_0: "false"', 'GIT_CONFIG_VALUE_0: "true"'),
        "gc": ("R35.maintenance", 'GIT_CONFIG_VALUE_1: "0"', 'GIT_CONFIG_VALUE_1: "1"'),
        "step-comment": ("R35.comments", "        # Binds the permitted publication language.\n", ""),
        "job-condition": ("R35.runnable", "    steps:\n", "    if: false\n    steps:\n"),
        "step-condition": ("R35.runnable", "        # Binds the permitted publication language.\n",
                           "        if: false\n        # Binds the permitted publication language.\n"),
        "ignored-exit": ("R35.runnable", "    steps:\n", "    continue-on-error: true\n    steps:\n"),
        "interval-comment": ("R35.scope", "intervals job", "secondary job"),
        "floating-ref": ("R36.ref", "          fetch-depth: 0", "          ref: main\n          fetch-depth: 0"),
        "ref-location": ("R36.location", '          python-version: "3.12"',
                         '          ref: ' + 'a' * 40 + '\n          python-version: "3.12"'),
        "publication-comment": ("R36.publication", "done commit", "later commit"),
        "secret": ("R37.secrets", "    steps:\n", "    token: ${{ secrets.FAKE }}\n    steps:\n"),
        "permissions": ("R37.permissions", "    steps:\n", "    permissions: write-all\n    steps:\n"),
        "extra-action": ("R37.actions", "actions/setup-python@v5", "actions/upload-artifact@v4"),
        "private-message": ("R39.message", f'echo "{PRIVATE_MESSAGE}"', 'echo "checked"'),
        "private-command": ("R39.command", f'echo "{PRIVATE_MESSAGE}"', PLAN_COMMANDS[9]),
        "freeze-comment": ("R40.location", "freeze_rehearsal.py", "later helper"),
        "freeze-command": ("R40.execution", f'echo "{PRIVATE_MESSAGE}"', "python3 evals/gap-study-4/freeze_rehearsal.py"),
        "local-suite": ("R41.local", f'echo "{PRIVATE_MESSAGE}"', "python3 tests/run_tests.py"),
        "copy-before": ("R42.branches", f"if [ ! -f {FROZEN} ]; then", f"if [ -f {FROZEN} ]; then"),
        "copy-head": ("R42.branches", 'git worktree add --detach "$copy_root" "$freeze"',
                      'git worktree add --detach "$copy_root" HEAD'),
        "copy-recent": ("R42.branches", "git log --format=%H --reverse", "git log --format=%H"),
        "copy-empty": ("R42.branches", '          test -n "$freeze"\n', ""),
        "copy-location": ("R42.branches", '$RUNNER_TEMP/frozen-tree', 'frozen-tree'),
        "copy-after": ("R42.branches", 'python3 "$copy_root/evals/gap-study-4/copy_manifest.py" --check', COPY),
        "copy-print": ("R42.branches", 'echo "copy gate commit: $freeze"', 'echo "copy checked"'),
        "copy-head-print": ("R42.branches", 'echo "copy gate commit: $(git rev-parse HEAD)"', 'echo "copy checked"'),
        "copy-cleanup": ("R42.branches", "trap 'git worktree remove \"$copy_root\"' EXIT", "true"),
        "copy-extra": ("R42.only", f'echo "{PRIVATE_MESSAGE}"', COPY),
        "zero-comment": ("R43.rule", "AFTER the freeze", "BEFORE the freeze"),
        "kickoff": ("R44.step", KICKOFF, BASE),
        "additive-assertion": ("R44.step", 'test "$removed" -eq 0', 'test "$removed" -ge 0'),
    }
    if BOX_DEFERRED in RAW:
        edits.update({
            "box-owner": ("R38.box-owner", BOX_OWNER, ""),
            "box-ruling": ("R38.box-ruling", BOX_RULING, ""),
            "box-premature": ("R38.box-absent", BOX_DEFERRED, BOX_DEFERRED + BOX_STEP),
            "box-indented": ("R44.step", BOX_DEFERRED,
                             "    " + BOX_OWNER + "    " + BOX_RULING),
        })
    language_step = ('      - name: Language rules\n'
                     '        # Binds the permitted publication language.\n'
                     f'        run: {BEFORE[0]}\n')
    separation_step = ('      - name: Separation of rounds\n'
                       "        # Binds the fresh baseline's prohibition on joining earlier counts.\n"
                       f'        run: {BEFORE[1]}\n')
    edits['before-wrapper'] = ('R38.before:' + BEFORE[0], f'        run: {BEFORE[0]}\n',
                              f'        run: |\n          echo ready\n          {BEFORE[0]}\n')
    edits['combined-steps'] = ('R38.separate', language_step + separation_step,
        language_step.replace(f'run: {BEFORE[0]}', f'run: |\n          {BEFORE[0]}\n          {BEFORE[1]}'))
    edits['extra-step'] = ('R38.total', '    steps:\n',
        '    steps:\n      - name: Extra\n        # A fake extra command.\n        run: echo extra\n')
    for name, command in (("push", "git push"), ("gh", "gh run list"), ("deploy", "deploy fake"),
                          ("upload", "upload fake"), ("release", "release fake"), ("network", "curl https://example.invalid")):
        edits[name] = ("R37." + name, f'echo "{PRIVATE_MESSAGE}"', command)
    for number, command in enumerate(BEFORE + AFTER, 1):
        if command == BOX and BOX_DEFERRED in RAW:
            continue
        edits[f"command-{number:02}"] = ("R38.command:" + command, command, command + " --missing")
    for number, command in enumerate(AFTER, 1):
        old = f"          if [ -f {FROZEN} ]; then\n            {COUNT_COMMAND}\n            {command}\n"
        edits[f"after-{number}"] = ("R38.after:" + command, old,
                                    old.replace(f"if [ -f {FROZEN} ]; then", "if true; then"))
        edits[f"empty-{number}"] = ("R43.count:" + command, old, old.replace(COUNT_COMMAND, "true"))
        edits[f"message-{number}"] = ("R38.after:" + command,
            f'{command}\n          else\n            echo "not applicable — not frozen"',
            f'{command}\n          else\n            echo "passed"')
    edits.update({
        "unnamed-push": ("R37.push", f"        run: {BEFORE[0]}\n",
                         f"        run: {BEFORE[0]}\n      - run: git push origin HEAD\n"),
        "unnamed-item": ("R37.step-keys", f"        run: {BEFORE[0]}\n",
                         f"        run: {BEFORE[0]}\n      - run: echo fake\n"),
        "checkout-repository": ("R37.checkout-keys", "          fetch-depth: 0\n",
                               "          fetch-depth: 0\n          repository: fake/repo\n"),
        "checkout-persist": ("R37.checkout-keys", "          fetch-depth: 0\n",
                            "          fetch-depth: 0\n          persist-credentials: true\n"),
        "setup-cache": ("R37.setup-keys", '          python-version: "3.12"\n',
                       '          python-version: "3.12"\n          cache: pip\n'),
        "job-container": ("R37.job-keys", "    steps:\n", "    container: fake\n    steps:\n"),
    })
    for name, clause, body in (
        ("push-option", "push", "git -C . push"),
        ("secret-index", "secrets", "${{ secrets['FAKE'] }}"),
        ("implicit-token", "secrets", "${{ github.token }}"),
        ("network-python", "network", "urllib"),
        ("network-client", "network", "requests"),
        ("network-remote", "network", "git ls-remote"),
    ):
        edits[name] = ("R37." + clause, '          test "$removed" -eq 0',
                       '          test "$removed" -eq 0\n          ' + body)
    for number, command in enumerate(BEFORE, 1):
        if command in (BOX, COPY):
            continue  # BOX has its two presence states; COPY has R42's exact body.
        edits[f"before-{number}"] = ("R38.before:" + command, f"        run: {command}\n",
            f"        run: |\n          echo fake\n          {command}\n")
    return edits


def altered(text, name):
    if name == "outside-block":
        return replace_once(text, "name: CI\n", "name: Other\n")
    if name == "introduced":
        return text
    if name == "trigger":
        return replace_once(text, "on:\n", "on:\n  workflow_dispatch:\n")
    if name == "removed-line":
        return replace_once(text, "name: CI\n", "")
    clause, old, new = mutations()[name]
    block = job_block(text)
    if block is None:
        raise AssertionError("one job is required before mutation")
    return text.replace(block, replace_once(block, old, new), 1)


def setUpModule():
    global RAW, CURRENT, BASE_TEXT, INTRODUCED, CURRENT_BOX_PRESENT
    BASE_TEXT, INTRODUCED = history(REPO)
    if SELECTED == "introduced":
        INTRODUCED = BASE
    RAW = (REPO / WORKFLOW).read_text(encoding="utf-8")
    CURRENT_BOX_PRESENT = True if SELECTED == "box-landed" else None
    CURRENT = altered(RAW, SELECTED) if SELECTED and SELECTED != "box-landed" else RAW


def tearDownModule():
    global RAW, CURRENT, BASE_TEXT, INTRODUCED, CURRENT_BOX_PRESENT
    RAW = CURRENT = BASE_TEXT = INTRODUCED = None
    CURRENT_BOX_PRESENT = None


class JobContract(unittest.TestCase):
    def clauses(self, prefix):
        issues = problems(CURRENT, BASE_TEXT, INTRODUCED, box_present=CURRENT_BOX_PRESENT)
        self.assertEqual([issue for issue in issues if issue.startswith(prefix + ".")], [])

    def test_outline(self):
        self.clauses("R35")

    def test_pin(self):
        self.clauses("R36")

    def test_boundary(self):
        self.clauses("R37")

    def test_commands(self):
        self.clauses("R38")

    def test_box_ownership(self):
        block = job_block(CURRENT)
        self.assertIsNotNone(block)
        if not (HERE / "tests/test_box_integration.py").is_file():
            self.assertIn(
                "# CP2 owns tests/test_box_integration.py; omitted until it exists",
                block,
            )
            self.assertIn("# under glitch-f3's section 10 box-integration ruling.", block)
            self.assertFalse(any(PLAN_COMMANDS[4] in run for _, _, run in steps(block)))

    def test_box_transition(self):
        # Both file-presence states are inputs in memory, never host fixtures.
        deferred = RAW.replace(BOX_STEP, BOX_DEFERRED) if BOX_STEP in RAW else RAW
        included = deferred.replace(BOX_DEFERRED, BOX_STEP)
        self.assertEqual(problems(deferred, BASE_TEXT, INTRODUCED, box_present=False), [])
        self.assertIn("R38.command:" + BOX,
                      problems(deferred, BASE_TEXT, INTRODUCED, box_present=True))
        self.assertEqual(problems(included, BASE_TEXT, INTRODUCED, box_present=True), [])
        self.assertIn("R38.box-absent",
                      problems(included, BASE_TEXT, INTRODUCED, box_present=False))

    def test_private_message(self):
        self.clauses("R39")

    def test_freeze_location(self):
        self.clauses("R40")

    def test_local_binding(self):
        self.clauses("R41")
        self.assertTrue(Path(scratch_git.__file__).resolve().is_relative_to(HERE.resolve()))

    def test_copy_boundary(self):
        self.clauses("R42")

    def test_zero(self):
        self.clauses("R43")

    def test_additions(self):
        self.clauses("R44")

    def test_future_pin(self):
        self.assertIsNotNone(job_block(RAW))
        for fake_ref in ("a" * 40, "F" * 40):
            block = job_block(RAW)
            unpinned = re.sub(r"^          ref: .*\n", "", block, flags=re.M)
            changed = RAW.replace(block, unpinned.replace("          fetch-depth: 0",
                                 f"          ref: {fake_ref}\n          fetch-depth: 0"))
            self.assertEqual(problems(changed, BASE_TEXT, INTRODUCED), [])

    def test_mutations(self):
        self.assertIsNotNone(job_block(RAW))
        expected = {name: entry[0] for name, entry in mutations().items()}
        expected.update(trigger="R37.trigger", **{"removed-line": "R44.additive",
                        "outside-block": "R37.outside", "introduced": "R44.kickoff"})
        for name, clause in expected.items():
            with self.subTest(name=name):
                self.assertIn(clause, problems(altered(RAW, name), BASE_TEXT, BASE if name == "introduced" else INTRODUCED))

    def test_kickoff_presence_before_comparison(self):
        addition = [run for name, _, run in steps(job_block(CURRENT))
                    if name == "Round 4 workflow diff is additive"]
        self.assertEqual(len(addition), 1)
        self.assertTrue(addition[0].startswith(f"git cat-file -e {KICKOFF}^{{commit}}\n"))
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            scratch_git.init(repo)
            result = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", KICKOFF + "^{commit}"],
                                    capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_absent_history(self):
        # A history-dependent reader fails loudly in a disposable repository.
        # No commit is made, and each repo still sets its own fake identity.
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder).resolve()
            scratch_git.init(repo)
            git(repo, "config", "user.name", "Fake Reader")
            git(repo, "config", "user.email", "fake-reader@example.invalid")
            with self.assertRaisesRegex(AssertionError, "git show"):
                history(repo)


if __name__ == "__main__":
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        del sys.argv[index:index + 2]
    outcome = unittest.main(verbosity=2, exit=False).result
    print(f"test_ci_job: {outcome.testsRun} run, {len(outcome.failures)} failures, "
          f"{len(outcome.errors)} errors, {len(outcome.skipped)} skipped")
    raise SystemExit(not outcome.wasSuccessful())
