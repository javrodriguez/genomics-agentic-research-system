#!/usr/bin/env python3
"""Mutant runner for the step-map extractor: every extraction rule must be able to fail.

Each mutant breaks one rule in a COPY of extract.py (the original is never edited), then the
test suite runs against that copy through STEPMAP_EXTRACT. A mutant the suite does not turn red
"survived": the rule it breaks is not actually checked. Each mutant's text must occur exactly
once in the extractor, or the runner stops (a mutant that matches nothing proves nothing).

    python3 evals/step-map/tests/mutants.py            # all mutants, one at a time
    python3 evals/step-map/tests/mutants.py fence 3a   # only mutants whose name contains these

Exit 0 only when every mutant is killed. Standard library only; one test process at a time.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(os.path.dirname(HERE), "extract.py")
TESTS = os.path.join(HERE, "test_extract.py")

# (name, rule it breaks, exact text in extract.py, replacement)
MUTANTS = [
    ("fence-blind", "a ``` line no longer opens a fence",
     'if line.lstrip().startswith("```"):\n            fenced.add(i)\n            inside = not inside',
     'if False:\n            fenced.add(i)\n            inside = not inside'),
    ("no-3a", "lettered sub-steps (3a) are not steps",
     'STEP_RE = re.compile(r"^(\\d+[a-z]?)\\.\\s")', 'STEP_RE = re.compile(r"^(\\d+)\\.\\s")'),
    ("steps-in-fences", "numbered lines inside a fence count as steps",
     '        if i in doc["fenced"]:\n            continue\n        m = STEP_RE.match',
     '        m = STEP_RE.match'),
    ("nonzero-narrow", '"Exit non-zero" covers only 1 and 2',
     'if m.group(1).startswith("non"):\n            codes |= {1, 2, 3}',
     'if m.group(1).startswith("non"):\n            codes |= {1, 2}'),
    ("no-paren-exit", "a parenthesised (exit 2) is not a branch",
     'EXIT_RE = re.compile(r"(?:\\bExit|\\(exit)\\s+', 'EXIT_RE = re.compile(r"(?:\\bExit)\\s+'),
    ("lowercase-exit", 'a lowercase "must exit non-zero" about a script counts as a branch',
     'EXIT_RE = re.compile(r"(?:\\bExit|\\(exit)\\s+', 'EXIT_RE = re.compile(r"(?i:\\bExit|\\(exit)\\s+'),
    ("no-question", "a template ending in ? is not a wait",
     'if para.rstrip().endswith("?"):\n        return "question"',
     'if False:\n        return "question"'),
    ("digit-tokens", "menu numbers count as fixed answers",
     'if re.fullmatch(r"[a-z]+", tok) and tok not in seen:',
     'if re.fullmatch(r"[a-z0-9, ]+", tok) and tok not in seen:'),
    ("ignore-subcommand", "a helper's subcommand is not part of the tool match",
     'if len(tokens) >= 3 and tokens[2] == argv[2]:', 'if len(tokens) >= 3:'),
    ("no-workspace-prefix", "<workspace>/_system/... does not map to a tool",
     'for prefix in ("<workspace>/", "$WS/", "./"):', 'for prefix in ("$WS/", "./"):'),
    ("no-prose-calls", "\"Run the wrapper's `check`\" is not a call",
     'PROSE_CALL_RE = re.compile(r"\\b[Rr]un (?:the wrapper\'s )?`(check|prepare|collect|summary)`")',
     'PROSE_CALL_RE = re.compile(r"(?!x)x")'),
    ("no-implicit-date", '"today\'s date" does not imply `date`',
     'for m in re.finditer(r"today\'s date", text):', 'for m in re.finditer(r"(?!x)x", text):'),
    ("no-argparse", "argparse's usage exit is not a site",
     'if isinstance(func, ast.Attribute) and func.attr == "parse_args":',
     'if isinstance(func, ast.Attribute) and func.attr == "parse_args_never":'),
    ("argparse-counts", "argparse-only codes count as emitted",
     'if c != "None" and any(s["how"] != "argparse" for s in sites))',
     'if c != "None" and sites)'),
    ("no-flag-pruning", "the command's flags decide no branch",
     '        if args_attr(test) and self.kinds.get(test.attr) == "bool":\n            return test.attr in self.present',
     '        if False:\n            return test.attr in self.present'),
    ("keep-fallthrough", "the unknown-command fall-through counts for every subcommand",
     '        if last >= 0 and k > last:\n            continue\n        common.append(stmt)',
     '        common.append(stmt)'),
    ("keep-no-command", "`if not args.cmd:` counts for every subcommand",
     '        if no_command(stmt):\n            continue\n        if names:',
     '        if names:'),
    ("drop-callee-raises", "a called helper's SystemExit is not followed",
     'if not returned and site["how"] not in ("raise", "sys.exit", "argparse"):',
     'if not returned:'),
    ("no-default-code", "a parametric exit code ignores the parameter's default",
     '            if isinstance(bound, tuple) and bound[0] == "default":\n                bound = self.index.codes(mod, bound[1], set())',
     '            if isinstance(bound, tuple) and bound[0] == "default":\n                bound = None'),
    ("exit-same-step-only", "an exit branch in the next step does not answer the previous call",
     '        if kind == "exit":\n            if current is not None:',
     '        if kind == "exit":\n            if current is not None and current["_k"] == k:'),
    ("branch-calls-open", "a call inside an exit branch opens a new region",
     'if first_in_step or not exit_since_open or current is None or current["_k"] != k:',
     'if True:'),
    ("all-bound", "a named key the helper never writes still binds",
     '        return {"text": text, "binding": "unbound", "label": inner}',
     '        return {"text": text, "binding": "key", "label": inner}'),
    ("no-dict-keys", "dict-literal keys are not in the vocabulary",
     '            if isinstance(node, ast.Dict):\n                vocab |=',
     '            if False:\n                vocab |='),
    ("no-after-label", "the word after <n> does not label it",
     '    after = re.match(r"\\s+([A-Za-z][A-Za-z0-9]*(?:\\(s\\))?)", line[end:])',
     '    after = None'),
    ("guard-allows-on-exit", "a guard denial reads as allow",
     'return {"allow": exc.code == 0 or exc.code is None,', 'return {"allow": True,'),
    ("intended-public", "stage 00 is judged in the public workspace",
     '    if contract_path.startswith("gars/00_") and tool and tool.startswith("stage00_register."):\n        return "fresh_declared"',
     '    if False:\n        return "fresh_declared"'),
    ("no-negation", '"Never add `--force`" is not a prohibition',
     'prohibited = bool(NEGATION_RE.search(text[sentence_start:m.start()]))', 'prohibited = False'),
    ("brackets-kept", "a bracketed [--flag] is not part of the command",
     'return {w.strip("[]").split("=")[0] for w in command.split() if w.strip("[]").startswith("--")}',
     'return {w.split("=")[0] for w in command.split() if w.startswith("--")}'),
    ("reads-ignored", "a template filled from files the agent reads gets a helper's keys",
     '            if reads:\n                break', '            if False:\n                break'),
    ("templates-dir-counts", "_templates/CONTEXT.md is a contract",
     'if p.endswith("/CONTEXT.md") and re.match(r"gars/0\\d_[^/]+/", p))',
     'if p.endswith("/CONTEXT.md") and re.match(r"gars/(0\\d_|_templates)", p))'),
    ("uninstantiable-guessed", "an unknown placeholder is filled with a guess",
     '            missing.append(m.group(0))\n            return m.group(0)',
     '            return "x"'),
    ("flag-target-last", "a flag modifies the last call in its step",
     '            target = before[-1] if before else (after[0] if after else None)',
     '            target = here[-1] if here else None'),
]


def run(selected):
    source = open(EXTRACT, encoding="utf-8").read()
    results = []
    for name, rule, old, new in MUTANTS:
        if selected and not any(s in name for s in selected):
            continue
        count = source.count(old)
        if count != 1:
            print("STOP: mutant %s matches %d places in extract.py (must be exactly 1)" % (name, count))
            return 2
        tmp = tempfile.mkdtemp(prefix="stepmap-mutant-")
        try:
            path = os.path.join(tmp, "extract.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(source.replace(old, new))
            env = dict(os.environ, STEPMAP_EXTRACT=path)
            start = time.time()
            proc = subprocess.run([sys.executable, TESTS], env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, universal_newlines=True, timeout=900)
            red = [ln.split(" ")[0] for ln in proc.stdout.splitlines()
                   if ln.endswith("... FAIL") or ln.endswith("... ERROR")]
            killed = proc.returncode != 0
            results.append((name, killed, red))
            print("%-24s %-7s %5.1fs  %s  [%s]" % (name, "killed" if killed else "SURVIVED",
                                                   time.time() - start, rule,
                                                   ", ".join(red[:4]) + (" ..." if len(red) > 4 else "")),
                  flush=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    survived = [r for r in results if not r[1]]
    print("mutants: %d run, %d killed, %d survived" % (len(results), len(results) - len(survived),
                                                       len(survived)))
    if not results:
        print("STOP: no mutant ran; an empty run is not a pass")
        return 2
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
