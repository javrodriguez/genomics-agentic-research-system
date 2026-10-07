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
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# The facts snapshot, by its test id: it fails on any change of output, so it never counts as a
# kill. Mutant runs skip it outright (RUN_ENV) and kills are read from the FAIL/ERROR id headers.
SNAPSHOT_TEST = "PublishedFactsTests.test_committed_facts_equal_a_fresh_extraction"
RUN_ENV = {"STEPMAP_NO_SNAPSHOT": "1"}
# The built-in negative control: it changes only what the facts say about themselves, so every
# rule-bound test must stay green. If it is "killed", the runner cannot tell a kill from noise.
CONTROL = "control-output-only"
HEADER_RE = re.compile(r"^(?:FAIL|ERROR): (\w+) \((?:[\w.]*\.)?(\w+)\.\w+\)", re.M)


def failed_tests(output):
    """Class.method of every failed or erroring test, from unittest's id headers."""
    return ["%s.%s" % (m.group(2), m.group(1)) for m in HEADER_RE.finditer(output)]


def kills(output):
    """The failures that count as a kill: every failed test except the facts snapshot."""
    return [t for t in failed_tests(output) if t != SNAPSHOT_TEST]
EXTRACT = os.path.join(os.path.dirname(HERE), "extract.py")
TESTS = os.path.join(HERE, "test_extract.py")

# (name, rule it breaks, exact text in extract.py, replacement)
MUTANTS = [
    (CONTROL, "negative control: only the facts' schema label changes, no rule",
     'SCHEMA = "stepmap-facts/1"', 'SCHEMA = "stepmap-facts/1-control"'),
    ("fence-blind", "a ``` line no longer opens a fence",
     'if line.lstrip().startswith("```"):\n            fenced.add(i)\n            inside = not inside',
     'if False:\n            fenced.add(i)\n            inside = not inside'),
    ("no-3a", "lettered sub-steps (3a) are not steps",
     'STEP_RE = re.compile(r"^(\\d+[a-z]?)\\.\\s")', 'STEP_RE = re.compile(r"^(\\d+)\\.\\s")'),
    ("steps-in-fences", "numbered lines inside a fence count as steps",
     '        if i in doc["fenced"]:\n            continue\n        m = STEP_RE.match',
     '        m = STEP_RE.match'),
    ("nonzero-fixed-set", '"Exit non-zero" handles a fixed {1, 2, 3}, not the call\'s own codes',
     '            site["handled"] |= {c for c in emitted if c != 0}',
     '            site["handled"] |= {1, 2, 3}'),
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
     '        if False and k in nonzero_in_step:'),
    ("same-tool-rerun", "a later call of the same tool is a re-run inside the open region",
     '        if current is not None and k in nonzero_in_step:',
     '        if current is not None and (k in nonzero_in_step or item["tool"] == current["tool"]):'),
    ("all-bound", "a named key the helper never writes still binds",
     '        return {"text": text, "binding": "unknown" if dynamic else "unbound", "label": label}',
     '        return {"text": text, "binding": "key", "label": label}'),
    ("unknown-never", "a missing key is unbound even where field names are computed at run time",
     '"binding": "unknown" if dynamic else "unbound"', '"binding": "unbound"'),
    ("unknown-always", "every missing key is unknown",
     '    dynamic = bool(getattr(vocab, "dynamic", None))', '    dynamic = True'),
    ("shape-blind-count", "a mapping, a name or a flag can bind a count",
     '                if shapes and shapes <= {"dict", "text", "bool"}:\n                    continue',
     '                if False:\n                    continue'),
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
     '        broken = evidence_holds(src, ruling["evidence"])\n        if broken:',
     '        broken = []\n        if broken:'),
    ("no-rerun", "'re-run `inspect` with ...' is not a call",
     'RERUN_RE = re.compile(r"\\bre-run `(\\w+)`(?: with `(--[^`]+)`)?")',
     'RERUN_RE = re.compile(r"(?!x)x")'),
    ("sanitized-generic", "the sanitized title is a context word, never graded",
     'GENERIC = {"n", "path", "title", "project_title", "raw",',
     'GENERIC = {"n", "path", "title", "project_title", "raw", "sanitized",'),
    ("no-class-forms", "finalize is graded for the public class only",
     '    if "<class>" in call["command"]:', '    if False:'),
    ("refused-calls-only", "refused flag variants are left out of the summary",
     '            elif not g["allowed_where_intended"]:\n                guard_refused.append(row)',
     '            elif False:\n                guard_refused.append(row)'),
    ("no-precondition-read", "the router's precondition check is not a file action",
     '    (r"\\bCheck preconditions: `01_samplesheets/<Assay ID>_samplesheet\\.csv` and `_design\\.csv` exist",',
     '    (r"(?!x)x",'),
    ("history-rules-off", "HISTORY.md appends are not file actions",
     '    actions.sort(key=lambda a: a["line"])',
     '    actions = [a for a in actions if not a["path"].endswith("HISTORY.md")]\n    actions.sort(key=lambda a: a["line"])'),
    ("ignore-exit-table", "a stage-wide exit table is not handling",
     '        if table and table["script"] == tool["argv"][1]:',
     '        if False:'),
    ("template-field-ignored", "a table row that needs the template field handles every site",
     '                if row["needs_template_field"]:\n                    if real and all(sets_template_field(src, s["at"]) for s in real):',
     '                if row["needs_template_field"]:\n                    if True:'),
    ("no-dict-keys", "dict-literal keys never reach the result",
     '        elif isinstance(node, ast.Dict):\n            for k, v in zip(node.keys, node.values):\n                if isinstance(k, ast.Constant) and isinstance(k.value, str):\n                    self.add_key(k.value, v)',
     '        elif isinstance(node, ast.Dict):\n            for k, v in zip(node.keys, node.values):\n                if False:\n                    self.add_key(k.value, v)'),
    ("module-wide-vocab", "a template binds against every key in the module, not the result's",
     '            vocab.merge(flow_vocabulary(index, registry, [call["tool"]], src, words))',
     '            vocab.merge(type("V", (dict,), {"dynamic": set()})({k: {"unknown"} for k in '
     'key_vocabulary(src, [module_for(call["tool"], registry)])}))'),
    ("no-key-domain", "keys computed at run time are never explained",
     '        if domain["site"] in flow.dynamic and not evidence_holds(src, domain["evidence"]):',
     '        if False:'),
    ("loop-anywhere", "a run-time key resolves from any loop that binds its name",
     '            if isinstance(n, ast.For) and n.lineno <= lineno <= (n.end_lineno or n.lineno):',
     '            if isinstance(n, ast.For):'),
    ("subscript-rebinds", "the write's own subscript counts as re-binding the loop variable",
     'x.id == name and isinstance(x.ctx, ast.Store)', 'x.id == name'),
    ("no-loop-tuple-target", "a tuple loop target never resolves",
     '                elif isinstance(n.target, ast.Tuple):', '                elif False:'),
    ("no-augassign-literals", "`+=` of literal tuples adds no keys",
     '                    base |= more', '                    pass'),
    ("tuple-is-a-key", "a tuple subscript is a run-time JSON key",
     '                    elif isinstance(sl, ast.Tuple) and not self.index.skipkeys:',
     '                    elif False:'),
    ("no-item-keys", "item-key rulings explain nothing",
     '            explained |= set(ruling["sites"])', '            pass'),
    ("dynamic-dropped", "run-time field keys are dropped silently",
     '                            self.dynamic.append("%s:%d" % (mod.path, lineno))',
     '                            pass'),
    ("graded-no-source", '"graded" counts placeholders with no backing call',
     'GRADED = ("key", "label", "unbound")', 'GRADED = ("key", "label", "unbound", "no_source")'),
    ("no-tuple-targets", "a, b = f() never carries the flow",
     '        keep = {i for i, el in enumerate(tgt.elts)\n                if isinstance(el, ast.Name) and el.id in tracked}',
     '        keep = set(range(len(tgt.elts)))'),
    ("no-param-backflow", "a callee's flowing parameter does not reach the caller's argument",
     '                for i in sorted(flowing):\n                    if i < len(node.args):',
     '                for i in []:\n                    if i < len(node.args):'),
    ("evidence-substring", "a cited line matches by substring",
     "        if len(lines) < line or lines[line - 1].rstrip() != expected.rstrip():",
     "        if len(lines) < line or expected.strip() not in lines[line - 1]:"),
    ("no-helper-recount", "a helper named outside backticks is not counted",
     '            "consistent": raw % 2 == 0 and raw // 2 == seen and helper_mentions == helper_calls}',
     '            "consistent": raw % 2 == 0 and raw // 2 == seen}'),
    ("spans-always-consistent", "the per-step span comparison is never made",
     '            "consistent": raw % 2 == 0 and raw // 2 == seen and helper_mentions == helper_calls}',
     '            "consistent": True}'),
    ("no-rerun-without", "'re-run without `--dry-run`' is not a call",
     'RERUN_WITHOUT_RE = re.compile(r"\\bre-run without `(--[a-z][a-z0-9-]*)`")',
     'RERUN_WITHOUT_RE = re.compile(r"(?!x)x")'),
    ("branch-calls-graded", "branch actions are presented as graded",
     '            b["graded"] = False', '            b["graded"] = True'),
    ("label-subset-reversed", "a label binds when its words are inside the key (any key with the word)",
     '                elif core <= words and len(ktoks - core) <= 1:',
     '                elif core <= words or words <= ktoks:'),
    ("total-is-a-count", "`total` counts as a count word",
     'COUNT_WORDS = {"count", "n", "num"}', 'COUNT_WORDS = {"count", "n", "num", "total"}'),
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
            env = dict(os.environ, STEPMAP_EXTRACT=path, **RUN_ENV)
            start = time.time()
            proc = subprocess.run([sys.executable, TESTS], env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, universal_newlines=True, timeout=900)
            red = kills(proc.stdout)
            killed = bool(red)
            results.append((name, killed, red))
            print("%-24s %-7s %5.1fs  %s  [%s]" % (name, "killed" if killed else "SURVIVED",
                                                   time.time() - start, rule,
                                                   ", ".join(red[:4]) + (" ..." if len(red) > 4 else "")),
                  flush=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    control = [r for r in results if r[0] == CONTROL]
    if control and control[0][1]:
        print("STOP: the negative control was 'killed' (%s); kills cannot be told from noise"
              % ", ".join(control[0][2]))
        return 2
    results = [r for r in results if r[0] != CONTROL]
    survived = [r for r in results if not r[1]]
    print("mutants: %d run, %d killed, %d survived" % (len(results), len(results) - len(survived),
                                                       len(survived)))
    if not results:
        print("STOP: no mutant ran; an empty run is not a pass")
        return 2
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
