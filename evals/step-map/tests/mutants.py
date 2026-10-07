#!/usr/bin/env python3
"""Mutant runner for the step-map extractor: every extraction rule must be able to fail.

Each mutant breaks one rule in a COPY of extract.py (the original is never edited), then the
test suite runs against that copy through STEPMAP_EXTRACT. A mutant counts as killed only when a
test OTHER than the published-facts snapshot fails: the snapshot fails on any change of output,
so a kill by it alone proves nothing about the rule. A mutant not killed that way "survived". Each mutant's text must occur exactly
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
     '        if current is not None and k in nonzero_in_step:',
     '        if False:'),
    ("all-bound", "a named key the helper never writes still binds",
     '        return {"text": text, "binding": "unbound", "label": inner}',
     '        return {"text": text, "binding": "key", "label": inner}'),
    ("no-dict-keys", "dict-literal keys are not in a subcommand's vocabulary",
     '            if isinstance(node, ast.Dict):\n                vocab |= {k.value for k in node.keys\n                          if isinstance(k, ast.Constant) and isinstance(k.value, str)}\n            elif isinstance(node, (ast.Assign, ast.AugAssign)):\n                targets = node.targets if isinstance(node, ast.Assign) else [node.target]\n                for tgt in targets:',
     '            if False:\n                pass\n            elif isinstance(node, (ast.Assign, ast.AugAssign)):\n                targets = node.targets if isinstance(node, ast.Assign) else [node.target]\n                for tgt in targets:'),
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
    ("no-boolop", "an and/or test is never decided by the flags",
     '        if isinstance(test, ast.BoolOp):\n            values',
     '        if False:\n            values'),
    ("user-exit-counts", "an exit the user reports counts as a branch on the agent's call",
     '            if actor == "agent":\n                events.append',
     '            if True:\n                events.append'),
    ("no-rulings", "reachability rulings are never applied",
     '            hit = [r["id"] for r in rulings if tool in r["tools"] and s["at"] == r["site"]]',
     '            hit = []'),
    ("rulings-unchecked", "a ruling holds whatever its evidence lines say",
     '            if len(lines) < line or needle not in lines[line - 1]:',
     '            if False:'),
    ("no-rerun", "'re-run `inspect` with ...' is not a call",
     'RERUN_RE = re.compile(r"\\bre-run `(\\w+)`(?: with `(--[^`]+)`)?")',
     'RERUN_RE = re.compile(r"(?!x)x")'),
    ("spans-always-consistent", "the independent backtick count is never compared",
     '            "consistent": raw % 2 == 0 and raw // 2 == seen and',
     '            "consistent": True or'),
    ("module-wide-vocab", "a template binds against every key in the module, not the called subcommand's",
     '        vocab = scoped_vocabulary(index, registry, backing) if backing else None',
     '        vocab = key_vocabulary(src, sorted({module_for(b, registry) for b in backing if module_for(b, registry)})) if backing else None'),
    ("loose-labels", "any one word of a label binds it",
     '        allowed = 1 if len(content) >= 3 else 0\n            for key in keys:',
     '        allowed = len(content) - 1\n            for key in keys:'),
    ("sanitized-generic", "the sanitized title is a context word, never graded",
     'GENERIC = {"n", "path", "title", "project_title", "raw",',
     'GENERIC = {"n", "path", "title", "project_title", "raw", "sanitized",'),
    ("no-class-forms", "finalize is graded for the public class only",
     '    if "<class>" in call["command"]:', '    if False:'),
    ("refused-calls-only", "refused flag variants are left out of the summary",
     '            elif not g["allowed_where_intended"]:\n                guard_refused.append(row)',
     '            elif False:\n                guard_refused.append(row)'),
    ("no-module-constants", "keys of the module constants a subcommand reads are ignored",
     '            for top in m.tree.body:\n                if isinstance(top, ast.Assign) and isinstance(top.value, ast.Dict) and \\',
     '            for top in []:\n                if isinstance(top, ast.Assign) and isinstance(top.value, ast.Dict) and \\'),
    ("no-precondition-read", "the router's precondition check is not a file action",
     '    (r"\\bCheck preconditions: `01_samplesheets/<Assay ID>_samplesheet\\.csv` and `_design\\.csv` exist",',
     '    (r"(?!x)x",'),
    ("history-rules-off", "HISTORY.md appends are not file actions",
     '    actions.sort(key=lambda a: a["line"])',
     '    actions = [a for a in actions if not a["path"].endswith("HISTORY.md")]\n    actions.sort(key=lambda a: a["line"])'),
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
            snapshot = [ln for ln in proc.stdout.splitlines()
                        if ("committed_facts" in ln or "re-derived and diffed" in ln)
                        and (ln.endswith("... FAIL") or ln.endswith("... ERROR"))]
            red = [r for r in red if not r.startswith("The")]
            bound = len([ln for ln in proc.stdout.splitlines()
                         if ln.endswith("... FAIL") or ln.endswith("... ERROR")]) - len(snapshot)
            killed = proc.returncode != 0 and bound > 0
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
