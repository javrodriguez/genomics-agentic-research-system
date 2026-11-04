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
from unittest import mock
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
# deferral; --regrade is the plan's command, the same complete check as --ledger (lane fold11/freeze-recheck).
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
# Fold 13, A3: inside the Copy record step's frozen branch, the freeze commit's code listing what HEAD added.
LATER = 'python3 "$copy_root/evals/gap-study-4/copy_manifest.py" --later-files "$(git rev-parse HEAD)"'
AFTER = PLAN_COMMANDS[-3:] + (
    "python3 evals/gap-study-4/result.py --check",
    "python3 evals/gap-study-4/completeness.py --check",
)
BEFORE = PLAN_COMMANDS[:9] + (PLAN_COMMANDS[10],)
# W8D (lane w8d, ruling W8D-gap4-1): W8A-R1-5 and W8A-R2-2, recorded for CP8 by glitch-1b's ruling W8A-close-2. The
# walk register's check runs as its own step, before and after the freeze alike (walks are pre-freeze records that
# stay): every walk folder bound to the one walk commit that wrote it. It is not one of plan 1013-1036's commands, so
# it is bound here beside them, never in their place, with the same single-command shape as BEFORE's steps.
WALK = "python3 evals/gap-study-4/walk_register.py --check"
WALK_STEP = (
    "      - name: Walk register\n"
    "        # Binds each registered walk to the one walk commit that wrote it; zero walks is said, not passed.\n"
    f"        run: {WALK}\n"
)
# Pre-freeze review 1, m14 (lane pf1-l2b, Sat 24 Oct 2026): round 3's two publication-language steps, ported. The
# published page's section is a single-command step like BEFORE's; the commit bodies' step reads the freeze commit
# and scans the bodies since it, or says it is not frozen, and its body is bound here exactly.
# Pre-freeze review 2, m5 (lane fold2-lb): an absent section exits 3 (not run); CI allows it only while no RESULT.md.
ABSENT_OK = " $(test -f evals/gap-study-4/RESULT.md || echo --allow-absent)"
SECTION = "python3 evals/gap-study-4/lint_pooling.py --section-of docs/EVALS.md" + ABSENT_OK
SECTION_LANGUAGE = ("python3 evals/gap-study-4/lint_language.py --section-of docs/EVALS.md"   # lane review 3
                    + ABSENT_OK)
BODIES = ('python3 evals/gap-study-4/lint_language.py --commits-since "$freeze"',
          'python3 evals/gap-study-4/lint_pooling.py --commits-since "$freeze"')
BODIES_RUN = (f"if [ -f {FROZEN} ]; then\n"
              f"  freeze=$(git log --format=%H --reverse -- {FROZEN} | head -1)\n"
              '  test -n "$freeze"\n'
              '  echo "scanning commit bodies since the freeze commit $freeze"\n'
              f"  {BODIES[0]}\n  {BODIES[1]}\n"
              "else\n"
              '  echo "not applicable — not frozen"\n'
              "fi")
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
    end = start + len(JOB)
    for line in text[end:].splitlines(keepends=True):
        if line.strip() and not line.lstrip().startswith("#") and not line.startswith(" " * 4):
            break
        end += len(line)
    return text[start:end]


def steps(block):
    result = []
    pattern = r"^      - name: ([^\n]+)\n(.*?)(?=^      - |\Z)"
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


def named_step_closed(body):
    lines = [line for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not lines or not lines[0].startswith("        run: "):
        return False
    return len(lines) == 1 or (lines[0] == "        run: |" and all(line.startswith(" " * 10) for line in lines[1:]))


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
    env_body = re.search(r"^    env:\n(.*?)(?=^    \S|\Z)", block, re.M | re.S)
    need(env_body is not None and env_body[0] == env, "R37.env-keys")
    need(all(named_step_closed(body) for _, body, _ in entries), "R37.run-keys")
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
    # The permitted YAML subset is closed before command clauses are read.
    need(re.findall(r"^    ([^ :]+):", active, re.M) == ["runs-on", "env", "steps"], "R37.job-keys")
    need(all(re.match(r"^      - (?:name: .+|uses: actions/(?:checkout@v4|setup-python@v5))$", line)
             for line in active.splitlines() if line.startswith("      - ")), "R37.step-keys")
    action_lines = lambda body: [line for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    checkout_lines = action_lines(checkout)
    checkout_without_ref = [line for line in checkout_lines if not re.fullmatch(r"          ref: [0-9a-fA-F]{40}", line)]
    need(checkout_without_ref == ["        with:", "          fetch-depth: 0"], "R37.checkout-keys")
    need(action_lines(setup) == ["        with:", '          python-version: "3.12"'], "R37.setup-keys")
    need(not re.search(r"\bsecrets\b|github\.token", active), "R37.secrets")
    need(not re.search(r"\bpermissions\s*:", active), "R37.permissions")
    for clause, pattern in (
        ("push", r"\bgit\b[^\n]*\bpush\b"), ("gh", r"\bgh\s+"),
        ("deploy", r"\bdeploy\b"), ("upload", r"\bupload(?:-artifact)?\b"),
        ("release", r"\brelease\b"), ("network", r"\b(?:curl|wget|fetch|clone|pip|npm|urllib|requests|ls-remote)\b|https?://"),
    ):
        # The exact admitted checkout option is not a shell fetch command.
        inspected = active.replace("          fetch-depth: 0", "") if clause == "network" else active
        need(not re.search(pattern, inspected, re.I), "R37." + clause)
    need(all(action in ("actions/checkout@v4", "actions/setup-python@v5")
             for action in re.findall(r"\buses:\s*(\S+)", active)), "R37.actions")

    if box_present is None:
        box_present = (HERE / "tests/test_box_integration.py").is_file()
    before = BEFORE if box_present else tuple(command for command in BEFORE if command != BOX)
    if not box_present:
        need(BOX_OWNER in block, "R38.box-owner")
        need(BOX_RULING in block, "R38.box-ruling")
        need(not any("test_box_integration.py" in run for run in runs), "R38.box-absent")
    before = before + (WALK, SECTION, SECTION_LANGUAGE)   # W8D: the walk register; m14: the published page, both linters
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
            '  python3 "$copy_root/evals/gap-study-4/copy_manifest.py" --check\n'
            f"  {LATER}\nfi"
        )
        need(run == expected_copy, "R42.branches")
    else:
        need(False, "R42.branches")
    need(sum("copy_manifest.py" in line for entry in runs for line in entry.splitlines()) == 3,
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
        f"git cat-file -e {introduced}^{{commit}}\n"
        f"removed=$(git diff {introduced} HEAD --numstat -- .github/workflows/ \\\n"
        "          | awk '{s+=$2} END {print s+0}')\n"
        'echo "workflow lines removed since the kickoff: $removed"\n'
        'test "$removed" -eq 0'
    )
    need(addition == [want_addition], "R44.step")
    need(bool(addition) and addition[0].startswith(f"git cat-file -e {KICKOFF}^{{commit}}\n"), "R44.present")
    removed = sum(i2 - i1 for tag, i1, i2, _, _ in
                  difflib.SequenceMatcher(a=baseline.splitlines(), b=text.splitlines(), autojunk=False).get_opcodes()
                  if tag in ("delete", "replace"))
    need(removed == 0, "R44.additive")
    bodies = [run for _, _, run in entries if any(command in run for command in BODIES)]
    need(bodies == [BODIES_RUN], "R38.bodies")            # m14 (lane pf1-l2b): the commit bodies' step, exactly
    need(len(entries) == len(expected) + 3, "R38.total")      # the bodies step, additive and the private message
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
        "copy-later-dropped": ("R42.branches", f"            {LATER}\n", ""),
        "copy-later-from-head": ("R42.branches", LATER, LATER.replace('"$copy_root/', "")),
        "copy-print": ("R42.branches", 'echo "copy gate commit: $freeze"', 'echo "copy checked"'),
        "copy-head-print": ("R42.branches", 'echo "copy gate commit: $(git rev-parse HEAD)"', 'echo "copy checked"'),
        "copy-cleanup": ("R42.branches", "trap 'git worktree remove \"$copy_root\"' EXIT", "true"),
        "copy-extra": ("R42.only", f'echo "{PRIVATE_MESSAGE}"', COPY),
        "zero-comment": ("R43.rule", "AFTER the freeze", "BEFORE the freeze"),
        "kickoff": ("R44.step", KICKOFF, BASE),
        "additive-assertion": ("R44.step", 'test "$removed" -eq 0', 'test "$removed" -ge 0'),
    }
    edits["kickoff-presence"] = ("R44.present", f"          git cat-file -e {KICKOFF}^{{commit}}\n", "")
    edits.update({
        "top-level-env": ("R37.outside", "", "env:\n  PYTHONPATH: fake\n"),
        "top-level-concurrency": ("R37.outside", "", "concurrency: fake\n"),
        **{"job-env-" + key.lower(): ("R37.env-keys", '      GIT_CONFIG_VALUE_1: "0"\n', '      GIT_CONFIG_VALUE_1: "0"\n      ' + key + ': fake\n') for key in ("PYTHONPATH", "GIT_DIR")},
        **{"run-key-" + key: ("R37.run-keys", f"        run: {BEFORE[0]}\n", extra + f"        run: {BEFORE[0]}\n") for key, extra in (
            ("env", "        env:\n          FAKE: fake\n"), ("timeout", "        timeout-minutes: 1\n"), ("with", "        with:\n          fake: fake\n"))},
    })
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
    edits["walk-step-removed"] = ("R38.command:" + WALK, WALK_STEP, "")       # W8D: the CI step taken out
    edits["command-walk"] = ("R38.command:" + WALK, WALK, WALK + " --missing")
    edits["before-walk"] = ("R38.before:" + WALK, f"        run: {WALK}\n",
                            f"        run: |\n          echo fake\n          {WALK}\n")
    edits["section-step-removed"] = ("R38.command:" + SECTION, SECTION, SECTION + " --missing")   # m14
    edits["before-section"] = ("R38.before:" + SECTION, f"        run: {SECTION}\n",
                               f"        run: |\n          echo fake\n          {SECTION}\n")
    edits["section-language-removed"] = ("R38.command:" + SECTION_LANGUAGE, SECTION_LANGUAGE,
                                         SECTION_LANGUAGE + " --missing")                      # lane review 3
    edits["before-section-language"] = ("R38.before:" + SECTION_LANGUAGE, f"        run: {SECTION_LANGUAGE}\n",
                                        f"        run: |\n          echo fake\n          {SECTION_LANGUAGE}\n")
    edits["bodies-unfrozen-pass"] = ("R38.bodies", '            echo "not applicable — not frozen"\n          fi\n',
                                     '            echo "passed"\n          fi\n')
    edits["bodies-since-head"] = ("R38.bodies", "git log --format=%H --reverse -- evals/gap-study-4/prereg.json | head -1)\n"
                                  '            test -n "$freeze"\n            echo "scanning',
                                  "git rev-parse HEAD)\n"
                                  '            test -n "$freeze"\n            echo "scanning')
    edits["bodies-one-linter"] = ("R38.bodies", f"            {BODIES[1]}\n", "")
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
    if SELECTED == "kickoff-registry-conditional" and BOX_DEFERRED not in RAW:
        edits.pop("kickoff-presence")
    return edits


def altered(text, name):
    if name in ("kickoff-registry-conditional", "run-first-line-only"):
        return text
    if name in ("top-level-env", "top-level-concurrency"):
        return text + mutations()[name][2]
    if name == "before-box":
        text = replace_once(text, BOX_DEFERRED, BOX_STEP) if BOX_DEFERRED in text else text
        return replace_once(text, f"        run: {BOX}\n",
                            f"        run: |\n          echo fake\n          {BOX}\n")
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
    CURRENT_BOX_PRESENT = True if SELECTED in ("box-landed", "before-box") else None
    CURRENT = altered(RAW, SELECTED) if SELECTED and SELECTED != "box-landed" else RAW
    if SELECTED == "box-landed" and BOX_STEP in RAW:
        # Wave 6 merge: the box step is in ci.yml now that S6 landed the file, so the witness takes it out
        # again: the file present and the workflow deferred must still be red by R38.command.
        CURRENT = replace_once(RAW, BOX_STEP, BOX_DEFERRED)
    if SELECTED == "run-first-line-only":
        def first_line_only(body):
            lines = [line for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")]
            return bool(lines and lines[0].startswith("        run: "))
        patch = mock.patch.object(sys.modules[__name__], "named_step_closed", first_line_only)
        patch.start()
        global CLOSURE_PATCH
        CLOSURE_PATCH = patch


def tearDownModule():
    global RAW, CURRENT, BASE_TEXT, INTRODUCED, CURRENT_BOX_PRESENT
    RAW = CURRENT = BASE_TEXT = INTRODUCED = None
    CURRENT_BOX_PRESENT = None
    if SELECTED == "run-first-line-only":
        CLOSURE_PATCH.stop()


class JobContract(unittest.TestCase):
    def clauses(self, prefix):
        issues = problems(CURRENT, BASE_TEXT, INTRODUCED, box_present=CURRENT_BOX_PRESENT)
        self.assertEqual([issue for issue in issues if issue.startswith(prefix + ".")], [])

    def test_outline(self):
        self.clauses("R35")

    def test_closed_structure(self):
        for tail in ("env:\n  PYTHONPATH: fake\n", "concurrency: fake\n"):
            with self.subTest(tail=tail):
                self.assertIn("R37.outside", problems(RAW + tail, BASE_TEXT, INTRODUCED))
        for key in ("PYTHONPATH", "GIT_DIR"):
            text = RAW.replace('      GIT_CONFIG_VALUE_1: "0"\n', '      GIT_CONFIG_VALUE_1: "0"\n      ' + key + ': fake\n')
            with self.subTest(key=key):
                self.assertIn("R37.env-keys", problems(text, BASE_TEXT, INTRODUCED))
        for extra in ("        env:\n          FAKE: fake\n", "        timeout-minutes: 1\n", "        with:\n          fake: fake\n"):
            text = RAW.replace(f"        run: {BEFORE[0]}\n", extra + f"        run: {BEFORE[0]}\n")
            with self.subTest(extra=extra):
                self.assertIn("R37.run-keys", problems(text, BASE_TEXT, INTRODUCED))
        for extra in ("        timeout-minutes: 1\n", "        env:\n          FAKE: fake\n"):
            for end in (f"        run: {BEFORE[0]}\n", '          test "$removed" -eq 0\n'):
                block = job_block(RAW)
                text = replace_once(RAW, block, replace_once(block, end, end + extra))
                with self.subTest(extra=extra, end=end):
                    self.assertIn("R37.run-keys", problems(text, BASE_TEXT, INTRODUCED), "R37.run-keys")

    def test_kickoff_registry_after_box(self):
        landed = RAW.replace(BOX_DEFERRED, BOX_STEP)
        with mock.patch.dict(globals(), RAW=landed):
            self.assertIn("kickoff-presence", mutations(), "R44.present:registry")

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
                        "outside-block": "R37.outside", "introduced": "R44.kickoff", "before-box": "R38.before:" + BOX})
        for name, clause in expected.items():
            with self.subTest(name=name):
                self.assertIn(clause, problems(altered(RAW, name), BASE_TEXT, BASE if name == "introduced" else INTRODUCED,
                                               box_present=True if name == "before-box" else None))

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



# Explicit Athena-only whole-file witnesses. Never called by ordinary imports
# or by a targeted Mac invocation. Three disjoint groups bound command time.
def witness_binding(name):
    if name == "run-first-line-only":
        return "JobContract.test_closed_structure", "R37.run-keys"
    if name == "kickoff-registry-conditional":
        return "JobContract.test_kickoff_registry_after_box", "R44.present:registry"
    special = {"trigger":"R37.trigger", "removed-line":"R44.additive",
               "outside-block":"R37.outside", "introduced":"R44.kickoff", "box-landed":"R38.command:" + BOX,
               "before-box":"R38.before:" + BOX}
    clause = special[name] if name in special else mutations()[name][0]
    method = {"R35":"test_outline", "R36":"test_pin", "R37":"test_boundary", "R38":"test_commands",
              "R39":"test_private_message", "R40":"test_freeze_location", "R41":"test_local_binding",
              "R42":"test_copy_boundary", "R43":"test_zero", "R44":"test_additions"}[clause.split(".")[0]]
    return "JobContract." + method, clause


def witness_names():
    return sorted(set(mutations()) | {"trigger", "removed-line", "outside-block", "introduced", "box-landed", "before-box", "kickoff-registry-conditional", "run-first-line-only"})


def witness_groups():
    names = witness_names()
    assert all(all(witness_binding(name)) for name in names)
    groups = [names[i::3] for i in range(3)]
    assert len(names) == len(set(names)) and names
    assert sorted(name for group in groups for name in group) == names
    assert sum(len(group) for group in groups) == len(names)
    return groups


def mutant_outcomes(result):
    """Rule B protocol line: every failing, erroring and skipped test id of one mutant run."""
    def ids(pairs):
        return [getattr(test, "test_case", test).id().removeprefix("__main__.") for test, _ in pairs]
    return {"failures": ids(result.failures), "errors": ids(result.errors), "skipped": ids(result.skipped)}


def run_witnesses(group):
    # Rule B (Javier, 11 Oct 2026, "gap4 witness rule B"): RED only when the bound
    # method fails by an AssertionError carrying the whole clause token; an error or
    # skip in the bound method fails the witness. Failures, errors and skips in other
    # methods of the same mutant run are never credited and never hidden: each is
    # printed per witness and totalled as collateral.
    import json
    import re
    import subprocess
    names = witness_groups()[group - 1]
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green(f"test_ci_job witnesses group {group}", [sys.executable, "-B", "-W", "ignore",
                                    str(Path(__file__).resolve())], timeout=1800, tag="test_ci_job")
    red = 0
    collateral = {}
    for name in names:
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name],
                             capture_output=True, text=True, timeout=180)
        lines = got.stdout + got.stderr
        # W5C-R4-3: the protocol lines are printed to stdout; read them from stdout only, the last match of each.
        summary = ([*re.finditer(r"^test_ci_job: (\d+) run, (\d+) failures, (\d+) errors, (\d+) skipped$",
                                 got.stdout, re.M)] or [None])[-1]
        recorded = re.findall(r"^test_ci_job outcomes: (\{.*\})$", got.stdout, re.M)
        method, clause = witness_binding(name)
        failures = re.findall(r"^FAIL: [^\n]*\(__main__\.([^)]*)\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)",
                              lines, re.M | re.S)
        attributed = any(bound == method and "AssertionError" in body and clause
                         and re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w:.-])", body)
                         for bound, body in failures)
        try:
            outcome = json.loads(recorded[-1]) if recorded else None
            consistent = bool(summary and outcome and all(
                isinstance(outcome[k], list) and len(outcome[k]) == int(summary[i])
                for k, i in (("failures", 2), ("errors", 3), ("skipped", 4))))
        except (ValueError, KeyError, TypeError):
            outcome, consistent = None, False
        bound_clean = consistent and method in outcome["failures"] and method not in outcome["errors"] \
            and method not in outcome["skipped"]
        passed = bool(attributed and bound_clean and got.returncode != 0 and "AssertionError" in lines)
        other = {k: [t for t in outcome[k] if t != method] for k in ("failures", "errors", "skipped")} if consistent else {}
        note = ("; collateral: " + ", ".join(f"{len(v)} {k} {sorted(set(v))}" for k, v in other.items())
                if any(other.values()) else ("; collateral: none" if consistent else "; outcomes line missing or inconsistent"))
        print(f"witness {name}: {'RED' if passed else 'FAIL'}; " + (summary[0] if summary else "missing summary") + note, flush=True)
        if not passed:
            print(lines, flush=True)
            return 1
        red += 1
        if any(other.values()):
            collateral[name] = other
    totals = {k: sum(len(v[k]) for v in collateral.values()) for k in ("failures", "errors", "skipped")}
    print(f"test_ci_job witnesses group {group}/3: {red}/{len(names)} red; registry {len(witness_names())}", flush=True)
    print(f"red without collateral: {red-len(collateral)}; red; collateral listed, never credited: {len(collateral)} {sorted(collateral)}", flush=True)
    print(f"collateral totals: {totals['failures']} failures, {totals['errors']} errors, {totals['skipped']} skipped", flush=True)
    return 0



class WitnessEvidence(unittest.TestCase):
    @staticmethod
    def fake_run(fails, errors=(), skips=(), text=None, clause=None, record=True, count=None):
        """A synthetic mutant run: FAIL blocks for `fails`, plus the outcomes line."""
        import json
        body = "".join(f"FAIL: fake (__main__.{m})\n---\nAssertionError: {text if text is not None else clause}\n"
                       for m in fails)
        body += "".join(f"ERROR: fake (__main__.{m})\n---\nValueError: fake\n" for m in errors)
        counts = count or (len(fails), len(errors), len(skips))
        body += f"test_ci_job: 1 run, {counts[0]} failures, {counts[1]} errors, {counts[2]} skipped\n"
        if record:
            body += f"test_ci_job outcomes: " + json.dumps({"failures": list(fails), "errors": list(errors),
                                                        "skipped": list(skips)}) + "\n"
        return mock.Mock(stdout=body, stderr="", returncode=1)

    @staticmethod
    def children(fake):
        """Lane t104-mutation-baseline: the runner's unmutated run (no --mutant) is green; each mutant run is `fake`."""
        green = mock.Mock(stdout="test_ci_job: 2 run, 0 failures, 0 errors, 0 skipped\n",
                          stderr="Ran 2 tests in 0.1s\n\nOK\n", returncode=0)
        return lambda argv, *a, **k: fake if "--mutant" in argv else green

    def outcome(self, name, fake):
        import contextlib, io
        out = io.StringIO()
        with mock.patch.object(sys.modules[__name__], "witness_groups", return_value=[[name], [], []]), \
             mock.patch.object(sys.modules[__name__], "witness_names", return_value=[name]), \
             mock.patch("subprocess.run", side_effect=self.children(fake)), contextlib.redirect_stdout(out):
            code = run_witnesses(1)
        return code, out.getvalue()

    def test_partition_and_attribution(self):
        names = witness_names()
        groups = witness_groups()
        self.assertEqual(sorted(n for group in groups for n in group), names)
        name = 'runner'
        method, clause = witness_binding(name)
        other = "Other.unrelated"
        for case, fake, expected in (
            ("bound only", self.fake_run([method], clause=clause), 0),
            ("collateral error", self.fake_run([method], errors=[other], clause=clause), 0),
            ("collateral failure and skip", self.fake_run([method, other], skips=[other], clause=clause), 0),
            ("other method only", self.fake_run([other], clause=clause), 1),
            ("bound error only", self.fake_run([], errors=[method], clause=clause), 1),
            ("bound failure and bound error", self.fake_run([method], errors=[method], clause=clause), 1),
            ("bound skip", self.fake_run([method], skips=[method], clause=clause), 1),
            ("no outcomes line", self.fake_run([method], clause=clause, record=False), 1),
            ("outcomes disagree with summary", self.fake_run([method], clause=clause, count=(1, 1, 0)), 1)):
            with self.subTest(case=case):
                code, printed = self.outcome(name, fake)
                self.assertEqual(code, expected)
                if case == "collateral error":
                    self.assertIn("collateral: 0 failures [], 1 errors ['Other.unrelated'], 0 skipped []", printed)
                    self.assertIn("red without collateral: 0; red; collateral listed, never credited: 1", printed)
                    self.assertNotIn("not credited, listed", printed)
                    self.assertIn("collateral totals: 0 failures, 1 errors, 0 skipped", printed)
                if case == "collateral failure and skip":
                    self.assertIn("1 failures ['Other.unrelated'], 0 errors [], 1 skipped ['Other.unrelated']", printed)
                if case == "bound only":
                    self.assertIn("collateral: none", printed)

    def test_protocol_lines_are_read_from_stdout_last_match(self):
        # W5C-R4-3: the summary and outcomes lines are read from stdout only, the last match of each.
        import json
        name = 'runner'
        method, clause = witness_binding(name)
        other = "Other.unrelated"
        stale = "test_ci_job: 9 run, 0 failures, 0 errors, 0 skipped\n"
        good = self.fake_run([method], errors=[other], clause=clause)
        forged = "test_ci_job outcomes: " + json.dumps({"failures": [method], "errors": [], "skipped": []}) + "\n"
        moved = self.fake_run([method], clause=clause)
        blocks, protocol = moved.stdout.split("test_ci_job: ", 1)
        for case, fake, expected in (
            ("earlier stale summary on stdout", mock.Mock(stdout=stale + good.stdout, stderr="", returncode=1), 0),
            ("forged outcomes on stderr", mock.Mock(stdout=good.stdout, stderr=forged, returncode=1), 0),
            ("forged summary on stderr", mock.Mock(stdout=good.stdout, stderr=stale, returncode=1), 0),
            ("protocol lines on stderr only", mock.Mock(stdout=blocks, stderr="test_ci_job: " + protocol, returncode=1), 1)):
            with self.subTest(case=case):
                code, printed = self.outcome(name, fake)
                self.assertEqual(code, expected, printed)
                if expected == 0:
                    self.assertIn("1 errors ['Other.unrelated']", printed)
                    self.assertIn("test_ci_job: 1 run, 1 failures, 1 errors, 0 skipped; collateral:", printed)

    def test_clause_tokens_are_exact(self):
        name = 'run-key-env'
        method, clause = witness_binding(name)
        for text, expected in ((clause, 0), (clause + ":extra", 1), (clause + "Extra", 1),
                             ("prefix-" + clause, 1), ("unrelated", 1)):
            with self.subTest(text=text):
                self.assertEqual(self.outcome(name, self.fake_run([method], text=text))[0], expected)


class RunChecksEcho(unittest.TestCase):
    """S4 (run_checks.py transferred from w1a): a PASSING command's witness summary lines are echoed into the
    athena log, so the log itself holds every group's collateral. No shell runs: subprocess.run is faked."""

    LINES = ("test_build_draft witnesses group 1/6: 41/41 red; registry 242",
             "test_ci_job witnesses group 2/3: 39/39 red; registry 116",
             "red without collateral: 1; red; collateral listed, never credited: 40 ['fake']",
             "collateral totals: 86 failures, 30 errors, 0 skipped")
    QUIET = ("witness fake: RED; test_ci_job: 1 run, 1 failures, 0 errors, 0 skipped; collateral: none",
             "fake prefix red without collateral: 0", " collateral totals: indented, not a summary line")

    def run_fake(self, code, stdout, stderr=""):
        import contextlib, io
        import run_checks
        out = io.StringIO()
        done = subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr=stderr)
        with mock.patch.object(run_checks.subprocess, "run", return_value=done), contextlib.redirect_stdout(out):
            k, n = run_checks.run_all([("fake.txt:1", "fake witness command")])
        return k, n, out.getvalue().splitlines()

    def test_passing_command_echoes_every_summary_line(self):
        k, n, printed = self.run_fake(0, "\n".join(self.QUIET[:1] + self.LINES[:2]) + "\n", "\n".join(self.LINES[2:] + self.QUIET[1:]) + "\n")
        self.assertEqual((k, n), (1, 1))
        self.assertTrue(printed[0].startswith("PASS [fake.txt:1] exit 0"), printed)
        self.assertEqual(printed[1:], ["    " + line for line in self.LINES], printed)

    def test_failing_command_keeps_its_tail(self):
        k, n, printed = self.run_fake(1, "\n".join(self.QUIET + self.LINES) + "\n")
        self.assertEqual((k, n), (0, 1))
        self.assertEqual(printed[1:], ["    " + line for line in self.QUIET + self.LINES], printed)


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        setUpModule()
        index = sys.argv.index("--witnesses")
        group = int(sys.argv[index + 1])
        if group not in (1,2,3):
            raise SystemExit("witness group must be 1, 2 or 3")
        raise SystemExit(run_witnesses(group))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        del sys.argv[index:index + 2]
    outcome = unittest.main(verbosity=2, exit=False).result
    print(f"test_ci_job: {outcome.testsRun} run, {len(outcome.failures)} failures, "
          f"{len(outcome.errors)} errors, {len(outcome.skipped)} skipped")
    if SELECTED is not None:
        import json
        print(f"test_ci_job outcomes: " + json.dumps(mutant_outcomes(outcome)))
    raise SystemExit(not outcome.wasSuccessful())
