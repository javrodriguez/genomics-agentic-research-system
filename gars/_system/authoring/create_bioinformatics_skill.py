#!/usr/bin/env python3
"""create-bioinformatics-skill — scaffold and verify a GARS pipeline wrapper.

The method behind this tool is `SKILL.md` beside it; this file is the deterministic half.
Anyone with a bioinformatics pipeline can use it to automate that pipeline the way GARS
automates its five assays.

Two subcommands, and the second is the important one:

  scaffold  Generate a new wrapper from a spec: the wrapper module, its SKILL.md, the
            sub-stage CONTEXT.md, and the registry rows to paste. Writes nothing that
            already exists; refuses rather than overwrite.
  conform   Lint a wrapper against the standard. This is what makes the standard real:
            it is run against the wrappers GARS already trusts, and a rule that fails a
            known-good wrapper is a wrong rule, not a wrong wrapper.

Exit codes are the stage-helper standard: 0 ok, 1 failure, 2 refused, 3 usage.
Runs on stock python 3.6.8, stdlib only -- the same interpreter contract as every
`_system/` helper, so the tool runs anywhere the wrappers run.
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2, 3

# The three verbs a wrapper exposes, in run order. Named here once; both the linter and the
# scaffold read them from this tuple so the two can never disagree.
VERBS = ("check", "prepare", "collect")

# Exit-code names a conforming wrapper imports from wrapperlib.
EXIT_NAMES = ("EXIT_OK", "EXIT_FAILURE", "EXIT_REFUSED", "EXIT_USAGE")


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


def fail(check, detail):
    return {"check": check, "detail": detail}


# --------------------------------------------------------------------------- conformance

def _module_of(wrapper_dir):
    """The wrapper's single python module, or None."""
    mods = sorted(p for p in wrapper_dir.glob("*.py") if not p.name.startswith("_"))
    return mods[0] if len(mods) == 1 else None


def _frontmatter(text):
    """The YAML-ish frontmatter block as raw lines. A narrow reader for a shape we own."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else None


def conform_one(wrapper_dir):
    """Every rule the standard makes checkable. Returns a list of failures (empty == passes).

    Each rule cites the decision or the lesson it enforces, so a wrapper author who trips one
    can read why it exists rather than guessing.
    """
    fails = []
    name = wrapper_dir.name

    # --- shape ---------------------------------------------------------------------------
    skill_md = wrapper_dir / "SKILL.md"
    if not skill_md.is_file():
        fails.append(fail("skill_md", "no SKILL.md in %s" % name))
    module = _module_of(wrapper_dir)
    if module is None:
        n = len([p for p in wrapper_dir.glob("*.py") if not p.name.startswith("_")])
        fails.append(fail("one_module",
                          "expected exactly one python module in %s, found %d -- a wrapper is "
                          "one file (decision 0028: clone the behaviour, not the architecture)"
                          % (name, n)))
        return fails

    src = module.read_text(encoding="utf-8")

    # --- the interpreter contract --------------------------------------------------------
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        fails.append(fail("syntax", "%s does not parse: %s" % (module.name, exc)))
        return fails

    if re.search(r'\bf"""|\bf"|\bf\'', src):
        fails.append(fail("py36",
                          "%s uses an f-string; the helpers run on stock python 3.6.8 "
                          "(environment.md), so use %% formatting" % module.name))

    # stdlib only: no import may name a third-party package.
    THIRD_PARTY = {"pandas", "numpy", "yaml", "scipy", "anndata", "scanpy", "requests",
                   "pydeseq2", "matplotlib", "sklearn"}
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods = [node.module.split(".")[0]]
        for m in mods:
            if m in THIRD_PARTY:
                fails.append(fail("stdlib_only",
                                  "%s imports %r; a wrapper is stdlib-only so it can run "
                                  "before any conda environment exists" % (module.name, m)))

    # --- the shared machinery ------------------------------------------------------------
    if "import wrapperlib" not in src:
        fails.append(fail("wrapperlib",
                          "%s does not import wrapperlib -- the shared machinery is what "
                          "keeps a wrapper a diff rather than a copy (decision 0028)"
                          % module.name))
    for exit_name in EXIT_NAMES:
        if exit_name not in src:
            fails.append(fail("exit_codes",
                              "%s never references %s; the standard is 0 ok / 1 failure / "
                              "2 refused / 3 usage" % (module.name, exit_name)))

    # --- identity ------------------------------------------------------------------------
    assigned = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name):
                assigned[tgt.id] = node.value
    for const in ("ASSAY", "SUBSTAGE"):
        if const not in assigned:
            fails.append(fail("identity", "%s declares no %s constant" % (module.name, const)))

    # The pin is derived, never restated. A literal version here is a second source of truth
    # that will drift from workspace.PIPELINES (decision 0028's honest version check).
    if "PIPELINE_VERSION" in assigned:
        node = assigned["PIPELINE_VERSION"]
        # Straddles two interpreters on purpose: ast.Str is gone in 3.12+, ast.Constant does
        # not exist in 3.6. getattr keeps the tool runnable on both, which it must be -- the
        # helpers target 3.6.8 while a developer's laptop may be far newer.
        str_node = getattr(ast, "Str", None)
        const_node = getattr(ast, "Constant", None)
        literal = bool(str_node and isinstance(node, str_node)) or bool(
            const_node and isinstance(node, const_node)
            and isinstance(getattr(node, "value", None), str))
        if literal:
            fails.append(fail("derived_pin",
                              "%s sets PIPELINE_VERSION to a literal; derive it from "
                              "ws.PIPELINES[ASSAY] so the pin has one source" % module.name))

    # --- the three verbs -----------------------------------------------------------------
    funcs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef,))}
    for verb in VERBS:
        if ("cmd_%s" % verb) not in funcs:
            fails.append(fail("verbs", "%s has no cmd_%s()" % (module.name, verb)))
    if "main" not in funcs:
        fails.append(fail("verbs", "%s has no main()" % module.name))

    # collect carries the model id: the contracts are executed by a model, so the model is
    # part of the toolchain that produced the result (decision 0024).
    # Matched as a complete quoted argparse flag, not as a substring: an earlier version of
    # this rule tested `"--model" in src` and a mutation renaming the flag to `--modelx`
    # sailed through it, because the rename still contains the string it searched for.
    if not re.search(r'''["']--model["']''', src):
        fails.append(fail("provenance",
                          "%s never declares a \"--model\" flag; collect must record the "
                          "executing model in its history entry (decision 0024)"
                          % module.name))

    # --- the exit gate -------------------------------------------------------------------
    if "OUTPUTS.tsv" not in src:
        fails.append(fail("registry",
                          "%s never writes OUTPUTS.tsv; a consumer finds inputs by artifact "
                          "type, not by hardcoded path (decision 0007)" % module.name))
    if "STATUS" not in src:
        fails.append(fail("status",
                          "%s never writes STATUS; it is the sole authority on sub-stage "
                          "state" % module.name))
    if "atomic_open" not in src:
        fails.append(fail("atomic_writes",
                          "%s writes without ws.atomic_open; a half-written artifact must "
                          "never be readable" % module.name))

    # --- the SKILL.md frontmatter --------------------------------------------------------
    if skill_md.is_file():
        fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
        if fm is None:
            fails.append(fail("skill_md", "%s/SKILL.md has no frontmatter block" % name))
        else:
            for key in ("name:", "description:", "source:", "pipeline:"):
                if key not in fm:
                    fails.append(fail("skill_md",
                                      "%s/SKILL.md frontmatter lacks %r -- the assay map reads "
                                      "these (decision 0012)" % (name, key.rstrip(":"))))
    return fails


def cmd_conform(args):
    roots = [Path(p) for p in args.wrapper]
    result = {"command": "conform", "ok": False, "wrappers": {}, "failures": []}
    targets = []
    for root in roots:
        if not root.is_dir():
            result["error"] = "no such directory: %s" % root
            return emit(result, EXIT_USAGE)
        # A directory of wrappers, or one wrapper.
        if (root / "SKILL.md").is_file() or list(root.glob("*.py")):
            targets.append(root)
        else:
            targets.extend(sorted(p for p in root.iterdir() if p.is_dir()))
    if not targets:
        result["error"] = "nothing to lint under: %s" % ", ".join(str(r) for r in roots)
        return emit(result, EXIT_USAGE)

    for target in targets:
        fails = conform_one(target)
        result["wrappers"][target.name] = {"ok": not fails, "failures": fails}
        for f in fails:
            item = dict(f)
            item["wrapper"] = target.name
            result["failures"].append(item)
    result["ok"] = not result["failures"]
    result["checked"] = len(targets)
    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)


# ----------------------------------------------------------------------------- scaffolding

REQUIRED_SPEC_KEYS = ("assay_id", "wrapper_name", "substage", "pipeline", "pipeline_version",
                      "samplesheet_header", "required_config_keys", "artifacts")


def validate_spec(spec):
    fails = []
    for key in REQUIRED_SPEC_KEYS:
        if key not in spec:
            fails.append(fail("spec", "missing required key %r" % key))
    if fails:
        return fails
    if not re.match(r"^[a-z][a-z0-9_]*$", spec["assay_id"]):
        fails.append(fail("spec", "assay_id %r must be lowercase snake_case (it becomes a "
                                  "directory name)" % spec["assay_id"]))
    if not re.match(r"^[a-z][a-z0-9-]*$", spec["wrapper_name"]):
        fails.append(fail("spec", "wrapper_name %r must be lowercase kebab-case"
                          % spec["wrapper_name"]))
    if not spec["artifacts"]:
        fails.append(fail("spec", "artifacts is empty: a sub-stage that produces nothing "
                                  "cannot be consumed by anything"))
    gate = [a for a in spec.get("artifacts", []) if a.get("content_gate")]
    if not gate:
        fails.append(fail("spec",
                          "no artifact carries content_gate: true -- an exit gate that only "
                          "checks existence once passed a table whose identifier column had "
                          "been silently dropped (decision 0010). Name the artifact whose "
                          "CONTENT proves every sample survived."))
    return fails


def module_source(spec):
    """The wrapper skeleton. Deliberately incomplete where judgment is genuine."""
    mod = spec["wrapper_name"].replace("-", "_")
    artifacts = spec["artifacts"]
    gate = [a for a in artifacts if a.get("content_gate")][0]
    header = spec["samplesheet_header"]
    req = spec["required_config_keys"]

    lines = []
    lines.append('#!/usr/bin/env python3')
    lines.append('"""GARS-authored wrapper for %s %s.'
                 % (spec["pipeline"], spec["pipeline_version"]))
    lines.append('')
    lines.append('Generated by create-bioinformatics-skill. The behavioural contract is')
    lines.append('decision 0028: one file, JSON on stdout, exit codes 0/1/2/3, deterministic')
    lines.append('artifacts written by code. Shared machinery lives in _system/wrapperlib.py;')
    lines.append('what is %s-specific here is the parameter translation and the exit gate.'
                 % spec["assay_id"])
    lines.append('')
    lines.append('  check    preflight; writes preflight/check_result.json')
    lines.append('  prepare  writes params.yaml, submit.sh and the reproducibility bundle')
    lines.append('  collect  the exit gate; writes OUTPUTS.tsv and STATUS')
    lines.append('')
    lines.append('Runs on stock python 3.6.8, stdlib only.')
    lines.append('"""')
    lines.append('')
    lines.append('import argparse')
    lines.append('import datetime')
    lines.append('import json')
    lines.append('import sys')
    lines.append('from pathlib import Path')
    lines.append('')
    lines.append('sys.path.insert(0, str(Path(__file__).resolve().parents[2]))')
    lines.append('import workspace as ws          # noqa: E402')
    lines.append('import wrapperlib as wl         # noqa: E402')
    lines.append('from wrapperlib import (EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE,   '
                 '# noqa: E402')
    lines.append('                        emit, fail)')
    lines.append('')
    lines.append('WORKSPACE = Path(__file__).resolve().parents[3]')
    lines.append('')
    lines.append('ASSAY = "%s"' % spec["assay_id"])
    lines.append('SUBSTAGE = "%s"' % spec["substage"])
    lines.append('# Derived, never restated: workspace.PIPELINES is the single source of the pin.')
    lines.append('PIPELINE_VERSION = ws.PIPELINES[ASSAY].rsplit("-", 1)[1]')
    lines.append('')
    lines.append('SAMPLESHEET_HEADER = %r' % (list(header),))
    lines.append('REQUIRED_KEYS = (')
    for k in req:
        lines.append('    "%s",' % k)
    lines.append(')')
    lines.append('')
    lines.append('')
    lines.append('def paths_for(project):')
    lines.append('    return {"substage": project / "02_bioinformatics" / ASSAY / SUBSTAGE,')
    lines.append('            "config": project / "_config" / ("%s.yaml" % ASSAY),')
    lines.append('            "samplesheet": project / "01_samplesheets" / '
                 '("%s_samplesheet.csv" % ASSAY),')
    lines.append('            "executor_config": project / "_config" / "nextflow.slurm.config"}')
    lines.append('')
    lines.append('')
    lines.append('def run_checks(project):')
    lines.append('    """Everything that must be true before a job may be submitted."""')
    lines.append('    fails = []')
    lines.append('    paths = paths_for(project)')
    lines.append('    cfg = {}')
    lines.append('    if not paths["config"].is_file():')
    lines.append('        fails.append(fail("preconditions", "no config at _config/%s.yaml" '
                 '% ASSAY))')
    lines.append('    else:')
    lines.append('        cfg = wl.read_config(paths["config"])')
    lines.append('        wl.check_config_common(cfg, REQUIRED_KEYS, fails)')
    lines.append('        # TODO(author): validate every closed-value choice against its tuple,')
    lines.append('        # and every path-valued key for readability. A wrong value here')
    lines.append('        # produces confident, wrong biology rather than an error.')
    lines.append('    wl.check_samplesheet(paths["samplesheet"], SAMPLESHEET_HEADER, fails)')
    lines.append('    checkout = wl.check_pipeline(ASSAY, fails)')
    lines.append('    wl.check_executor_config(paths["executor_config"], fails)')
    lines.append('    wl.check_run_dir(paths["substage"], fails)')
    lines.append('    paths["checkout"] = checkout')
    lines.append('    return fails, cfg, paths')
    lines.append('')
    lines.append('')
    lines.append('def cmd_check(args):')
    lines.append('    project = Path(args.project)')
    lines.append('    result = {"command": "check", "ok": False, "assay": ASSAY, "failures": []}')
    lines.append('    if not project.is_dir():')
    lines.append('        result["error"] = "no such project: %s" % project')
    lines.append('        return emit(result, EXIT_USAGE)')
    lines.append('    fails, cfg, paths = run_checks(project)')
    lines.append('    result["failures"] = fails')
    lines.append('    result["ok"] = not fails')
    lines.append('    preflight = paths["substage"] / "preflight"')
    lines.append('    preflight.mkdir(parents=True, exist_ok=True)')
    lines.append('    with ws.atomic_open(preflight / "check_result.json") as fh:')
    lines.append('        json.dump({"ok": result["ok"], "failures": fails,')
    lines.append('                   "pipeline": ws.PIPELINES[ASSAY],')
    lines.append('                   "wrapper": "%s"}, fh, indent=2, sort_keys=True)'
                 % spec["wrapper_name"])
    lines.append('    result["wrote"] = str((preflight / "check_result.json")'
                 '.relative_to(project))')
    lines.append('    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)')
    lines.append('')
    lines.append('')
    lines.append('def build_params(cfg, paths):')
    lines.append('    """The audited translation of _config/<assay>.yaml into pipeline params.')
    lines.append('')
    lines.append('    Every key the pipeline receives is listed here -- the agent never')
    lines.append('    composes one.')
    lines.append('    """')
    lines.append('    params = [')
    lines.append('        ("input", str(paths["samplesheet"].resolve())),')
    lines.append('        ("outdir", str((paths["substage"] / "run" / "results").resolve())),')
    lines.append('    ]')
    lines.append('    # TODO(author): translate each required config key into its pipeline')
    lines.append('    # parameter. Read the pipeline\'s nextflow_schema.json for the real names.')
    lines.append('    return params')
    lines.append('')
    lines.append('')
    lines.append('def cmd_prepare(args):')
    lines.append('    project = Path(args.project)')
    lines.append('    result = {"command": "prepare", "ok": False, "assay": ASSAY, '
                 '"failures": []}')
    lines.append('    if not project.is_dir():')
    lines.append('        result["error"] = "no such project: %s" % project')
    lines.append('        return emit(result, EXIT_USAGE)')
    lines.append('    fails, cfg, paths = run_checks(project)')
    lines.append('    if fails:')
    lines.append('        result["failures"] = fails')
    lines.append('        result["error"] = ("preflight failed; nothing written. Run `check` "')
    lines.append('                           "for the same detail.")')
    lines.append('        return emit(result, EXIT_FAILURE)')
    lines.append('')
    lines.append('    substage = paths["substage"]')
    lines.append('    substage.mkdir(parents=True, exist_ok=True)')
    lines.append('    (substage / "logs").mkdir(exist_ok=True)')
    lines.append('')
    lines.append('    params = build_params(cfg, paths)')
    lines.append('    wl.write_params_yaml(substage, ASSAY, params)')
    lines.append('')
    lines.append('    work_dir = "%s/%s-%s" % (cfg["compute.work_dir"].rstrip("/"),')
    lines.append('                             project.resolve().name, ASSAY)')
    lines.append('    body = """nextflow run "{checkout}" \\\\')
    lines.append('    -profile apptainer \\\\')
    lines.append('    -c "{executor_config}" \\\\')
    lines.append('    -params-file "{substage}/params.yaml" \\\\')
    lines.append('    -work-dir "{work_dir}" \\\\')
    lines.append('    $RESUME""".format(checkout=paths["checkout"],')
    lines.append('                      executor_config=paths["executor_config"].resolve(),')
    lines.append('                      substage=substage.resolve(), work_dir=work_dir)')
    lines.append('    wl.write_submit_sh(substage, WORKSPACE, cfg, project.resolve().name,')
    lines.append('                       ASSAY, body)')
    lines.append('    wl.write_reproducibility(substage, ASSAY, paths["checkout"],')
    lines.append('                             {"samplesheet": paths["samplesheet"],')
    lines.append('                              "config": paths["config"]}, params)')
    lines.append('')
    lines.append('    result.update({"ok": True,')
    lines.append('                   "wrote": ["params.yaml", "submit.sh",')
    lines.append('                             "reproducibility/manifest.json",')
    lines.append('                             "reproducibility/commands.sh"],')
    lines.append('                   "params": dict(params),')
    lines.append('                   "submit": str((substage / "submit.sh").resolve()),')
    lines.append('                   "samples": wl.samplesheet_samples(paths["samplesheet"])})')
    lines.append('    return emit(result, EXIT_OK)')
    lines.append('')
    lines.append('')
    lines.append('def cmd_collect(args):')
    lines.append('    project = Path(args.project)')
    lines.append('    result = {"command": "collect", "ok": False, "assay": ASSAY, '
                 '"failures": []}')
    lines.append('    if not project.is_dir():')
    lines.append('        result["error"] = "no such project: %s" % project')
    lines.append('        return emit(result, EXIT_USAGE)')
    lines.append('    paths = paths_for(project)')
    lines.append('    substage = paths["substage"]')
    lines.append('    if not (substage / "run" / ".gars_run_complete").is_file():')
    lines.append('        result["error"] = ("run/.gars_run_complete is absent: the pipeline "')
    lines.append('                           "has not finished (or crashed before the marker). "')
    lines.append('                           "collect gates on completion, it does not wait "')
    lines.append('                           "for it.")')
    lines.append('        return emit(result, EXIT_REFUSED)')
    lines.append('')
    lines.append('    cfg = wl.read_config(paths["config"])')
    lines.append('    results = substage / "run" / "results"')
    lines.append('    samples = wl.samplesheet_samples(paths["samplesheet"])')
    lines.append('    fails = []')
    lines.append('')
    lines.append('    # The exit gate. CONTENT, not existence (decision 0010): the gate below')
    lines.append('    # must prove every sample survived the pipeline, because a sample lost to')
    lines.append('    # a failed process disappears here and nowhere downstream.')
    lines.append('    # TODO(author): resolve each artifact path and check it is real.')
    lines.append('    outputs = []')
    for a in artifacts:
        lines.append('    #   %-22s <- %s' % (a["type"], a.get("path", "<path>")))
    lines.append('    # TODO(author): the content gate on %r -- assert every sample id appears'
                 % gate["type"])
    lines.append('    # in it, and fail naming the missing ones.')
    lines.append('')
    lines.append('    if fails:')
    lines.append('        result["failures"] = fails')
    lines.append('        return emit(result, EXIT_FAILURE)')
    lines.append('')
    lines.append('    with ws.atomic_open(substage / "OUTPUTS.tsv") as fh:')
    lines.append('        fh.write("# type\\trole\\tpath\\n")')
    lines.append('        for typ, path in outputs:')
    lines.append('            fh.write("%s\\tnative\\t%s\\n" % (typ, path))')
    lines.append('')
    lines.append('    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")')
    lines.append('    with ws.atomic_open(substage / "STATUS") as fh:')
    lines.append('        fh.write("COMPLETE %s\\n" % now)')
    lines.append('')
    lines.append('    version = ws.template_version(WORKSPACE)')
    lines.append('    model = args.model or "unknown"')
    lines.append('    entry = "\\n".join([')
    lines.append('        "## <ISO-8601 date> — 02_bioinformatics/%s/%s — pipeline complete"')
    lines.append('        % (ASSAY, SUBSTAGE),')
    lines.append('        "",')
    lines.append('        "Template version: %s" % version,')
    lines.append('        "Model: %s" % model,')
    lines.append('        "Pipeline: %s %%s (local checkout)" %% PIPELINE_VERSION,'
                 % spec["pipeline"])
    lines.append('        "Samples: %d (%s)" % (len(samples), ", ".join(samples)),')
    lines.append('        "Outputs: " + ", ".join("`%s`" % t for t, _ in outputs),')
    lines.append('    ])')
    lines.append('    result.update({"ok": True,')
    lines.append('                   "outputs": [{"type": t, "path": p} for t, p in outputs],')
    lines.append('                   "samples": samples, "template_version": version,')
    lines.append('                   "model": model, "history_entry": entry})')
    lines.append('    return emit(result, EXIT_OK)')
    lines.append('')
    lines.append('')
    lines.append('def main(argv=None):')
    lines.append('    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])')
    lines.append('    sub = ap.add_subparsers(dest="cmd")')
    lines.append('    for name, needs_model in (("check", False), ("prepare", False),')
    lines.append('                              ("collect", True)):')
    lines.append('        p = sub.add_parser(name)')
    lines.append('        p.add_argument("--project", required=True)')
    lines.append('        if needs_model:')
    lines.append('            p.add_argument("--model", default="unknown",')
    lines.append('                           help="the exact model id of the agent executing "')
    lines.append('                                "this sub-stage (decision 0024)")')
    lines.append('    args = ap.parse_args(argv)')
    lines.append('    if not args.cmd:')
    lines.append('        ap.print_help(sys.stderr)')
    lines.append('        return EXIT_USAGE')
    lines.append('    return {"check": cmd_check, "prepare": cmd_prepare,')
    lines.append('            "collect": cmd_collect}[args.cmd](args)')
    lines.append('')
    lines.append('')
    lines.append('if __name__ == "__main__":')
    lines.append('    sys.exit(main())')
    return "\n".join(lines) + "\n"


def skill_md_source(spec):
    bins = spec.get("requires_bins", ["python3", "nextflow", "java", "git"])
    return "\n".join([
        "---",
        "name: %s" % spec["wrapper_name"],
        "description: >",
        "  GARS-authored wrapper around %s %s: preflight, audited params translation,"
        % (spec["pipeline"], spec["pipeline_version"]),
        "  Slurm submission script with requeue guard, content-checking exit gate and",
        "  artifact registry rows.",
        "metadata:",
        "  openclaw:",
        "    source: gars                    # versioned in this repo (decision 0012)",
        "    pipeline: %s" % spec["pipeline"],
        '    pipeline_version: "%s"' % spec["pipeline_version"],
        "    requires:",
        "      bins: [%s]" % ", ".join(bins),
        '      python: ">=3.6 (stdlib only)"',
        "    install: >",
        "      Nothing to install for the wrapper itself. Runtime needs the gars-nxf conda",
        "      environment on PATH at submit time, and a pinned local checkout of",
        "      %s %s." % (spec["pipeline"], spec["pipeline_version"]),
        "---",
        "",
        "# %s" % spec["wrapper_name"],
        "",
        "One stdlib Python file, JSON on stdout, exit codes `0 ok / 1 failure / 2 refused /",
        "3 usage`. The sub-stage contract at",
        "`02_bioinformatics/%s/%s/CONTEXT.md` orchestrates it;" % (spec["assay_id"],
                                                                   spec["substage"]),
        "nothing here is invoked directly by a user.",
        "",
        "```",
        "python3 %s.py check   --project projects/<title>"
        % spec["wrapper_name"].replace("-", "_"),
        "python3 %s.py prepare --project projects/<title>"
        % spec["wrapper_name"].replace("-", "_"),
        "sbatch <substage>/submit.sh                       # written by prepare",
        "python3 %s.py collect --project projects/<title> --model \"<model id>\""
        % spec["wrapper_name"].replace("-", "_"),
        "```",
        "",
        "- `check` — preflight: config complete and sane, samplesheet header and paths,",
        "  pinned checkout tag verified, executor config carries no `params` block, `run/`",
        "  safe to use. Writes `preflight/check_result.json`.",
        "- `prepare` — re-validates, then writes `params.yaml`, `submit.sh` and",
        "  `reproducibility/{manifest.json,commands.sh}`. Deterministic bytes.",
        "- `collect` — the exit gate: content-checked, not existence-checked. Writes",
        "  `OUTPUTS.tsv` and `STATUS`, returns the `history_entry` to append verbatim.",
        "",
        "## Produced artifacts",
        "",
        "| Type | Path |",
        "|---|---|",
    ] + ["| `%s` | `%s` |" % (a["type"], a.get("path", "<to be filled>"))
         for a in spec["artifacts"]] + [""])


def registry_rows(spec):
    """The lines a human pastes into the registries. Never written automatically: these are
    shared files, and a generator that edits them turns a review into a merge conflict."""
    arts = ", ".join(a["type"] for a in spec["artifacts"])
    return {
        "workspace.PIPELINES": '    "%s": "%s-%s",'
                               % (spec["assay_id"],
                                  spec["pipeline"].replace("/", "-"),
                                  spec["pipeline_version"]),
        "assay_stage_skill_map.md": "| %s | %s | 02_bioinformatics | %s | %s | gars | "
                                    "samplesheet | %s |"
                                    % (spec.get("assay_label", spec["assay_id"]),
                                       spec["assay_id"], spec["substage"],
                                       spec["wrapper_name"], arts),
    }


def cmd_scaffold(args):
    result = {"command": "scaffold", "ok": False, "failures": [], "wrote": []}
    spec_path = Path(args.spec)
    if not spec_path.is_file():
        result["error"] = "no such spec: %s" % spec_path
        return emit(result, EXIT_USAGE)
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        result["error"] = "spec is not valid JSON: %s" % exc
        return emit(result, EXIT_USAGE)

    fails = validate_spec(spec)
    if fails:
        result["failures"] = fails
        return emit(result, EXIT_FAILURE)

    out = Path(args.out)
    wrapper_dir = out / spec["wrapper_name"]
    module = wrapper_dir / (spec["wrapper_name"].replace("-", "_") + ".py")
    skill = wrapper_dir / "SKILL.md"

    existing = [str(p) for p in (module, skill) if p.exists()]
    if existing and not args.force:
        result["error"] = ("refusing to overwrite: %s. A wrapper already there is someone's "
                           "work; pass --force only if you mean it."
                           % ", ".join(existing))
        return emit(result, EXIT_REFUSED)

    if not args.dry_run:
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        module.write_text(module_source(spec), encoding="utf-8")
        skill.write_text(skill_md_source(spec), encoding="utf-8")
    result["wrote"] = [str(module), str(skill)]
    result["registry_rows"] = registry_rows(spec)
    result["next_steps"] = [
        "Fill every TODO(author) in %s -- they mark where judgment is genuine." % module.name,
        "Paste the registry_rows above into workspace.PIPELINES and "
        "_references/assay_stage_skill_map.md.",
        "Write the sub-stage CONTEXT.md against _references/contract_standard.md's eight "
        "sections.",
        "Run `conform` on the wrapper directory until it passes.",
        "Add an offline test to tests/run_tests.py, then a real -profile test run.",
    ]
    result["ok"] = True
    result["dry_run"] = bool(args.dry_run)
    return emit(result, EXIT_OK)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("conform", help="lint wrappers against the standard")
    p.add_argument("wrapper", nargs="+",
                   help="a wrapper directory, or a directory of wrapper directories")

    p = sub.add_parser("scaffold", help="generate a new wrapper from a spec")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", required=True, help="the wrappers directory to write into")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help(sys.stderr)
        return EXIT_USAGE
    return {"conform": cmd_conform, "scaffold": cmd_scaffold}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
