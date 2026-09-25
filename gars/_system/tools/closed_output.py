"""What a typed call may return from a non-public project (row 13 step B; decision 0141).

Two things live here, and both the dispatcher (`_system/tool_call.py`) and the cluster-side
`scripts/bring_home.py` import them, so there is one keep-list, never two:

- `closed(path_args, workspace, cwd)`: whether a call's strings reach a closed project, judged
  with 0107's own reader in `_system/guard_hook.py` (imported, never copied). A call on a closed
  project is filtered; a path outside the workspace while any non-public project exists, or a
  closed project named together with a path outside it, is refused before anything runs.
- `filter_output(tool_name, stdout, stderr, exit_code)`: the keep-lists. Only the listed keys
  survive, each sanitized by its rule; every other value becomes `WITHHELD`; output that does
  not parse becomes `{"withheld": true, "exit_code": <n>}`; stderr is withheld with its line
  count kept. A failure entry keeps its code, never its detail. The pilot log's keep-list `*`
  ("all") keeps each stdout line that has one of the writer's fixed formats, and no other.

Stdlib only; written for Python 3.6.8, like every `_system/` helper.
"""
import json
import os
import re
import sys
from pathlib import Path

SYSTEM = Path(__file__).resolve().parents[1]
if str(SYSTEM) not in sys.path:
    sys.path.insert(0, str(SYSTEM))
import guard_hook  # noqa: E402  0107's closed-project reader, imported, never copied

WITHHELD = "withheld: non-public project (0141)"
REFUSALS = ("path_outside_workspace", "path_outside_closed_project", "path_not_fixed_layout")

CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
STATE_CODES = ("PENDING", "SUBMITTED", "RUNNING", "VALIDATING", "COMPLETED", "COMPLETE",
               "FAILED", "CANCELLED", "ARTIFACT_MISSING")
JOB_ID = re.compile(r"^[0-9]{1,20}(?:_[0-9]{1,10})?$")
VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]{0,39}$")
MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,79}$")
SUBSTAGE = re.compile(r"^(?:[0-9]{2}_[a-z0-9-]{1,48}|01_prepare_samplesheets)$")
# The fixed layout a `resolved` value may take: stage 01's two emitted tables, or a file a GARS
# wrapper writes under its own sub-stage folder. Anything else (a path a human placed, a sample
# name in a file name) is withheld.
LAYOUT = re.compile(
    r"^(?:01_samplesheets/[a-z0-9_]{1,40}_(?:samplesheet|design)\.csv"
    r"|02_bioinformatics/[a-z0-9_]{1,40}/[0-9]{2}_[a-z0-9-]{1,48}/"
    r"(?:run/tables/(?:de_results|normalized_counts)\.csv"
    r"|adapted/(?:counts_gene|gene_id_to_name)\.tsv"
    r"|run/results/(?:star_salmon|star_rsem|salmon)/salmon\.merged\."
    r"(?:gene_counts_length_scaled|gene_counts|transcript_counts|gene_tpm)\.tsv))$")
# prepare's `wrote` names, fixed by the wrappers.
FIXED_NAMES = ("scripts/run_de.py", "submit.sh", "reproducibility/manifest.json",
               "reproducibility/commands.sh")


def _code(value):
    return value if isinstance(value, str) and CODE.match(value) else WITHHELD


def _bool(value):
    return value if isinstance(value, bool) else WITHHELD


def _failures(value):
    """Each failure keeps its code (`check`), never its detail (review m8)."""
    if not isinstance(value, list):
        return WITHHELD
    return [{"check": _code(f.get("check")), "detail": WITHHELD} if isinstance(f, dict)
            else WITHHELD for f in value]


def _wrote(value):
    if not isinstance(value, list):
        return WITHHELD
    return [v if v in FIXED_NAMES else WITHHELD for v in value]


def _outputs(value):
    if not isinstance(value, list):
        return WITHHELD
    return [{"type": _code(o.get("type")), "role": _code(o.get("role")), "path": WITHHELD}
            if isinstance(o, dict) else WITHHELD for o in value]


def _missing(value):
    """resolve_artifact's `missing`: the types only; each reason is withheld."""
    if not isinstance(value, dict):
        return WITHHELD
    return dict((key, WITHHELD) for key in value if CODE.match(key))


def _resolved(value):
    """resolve_artifact's `resolved`: per type its sub-stage, and the path only when it is the
    fixed sub-stage layout."""
    if not isinstance(value, dict):
        return WITHHELD
    kept = {}
    for key, entry in value.items():
        if not CODE.match(key) or not isinstance(entry, dict):
            continue
        substage = entry.get("substage")
        resolved = entry.get("resolved")
        kept[key] = {
            "substage": substage if isinstance(substage, str) and SUBSTAGE.match(substage)
            else WITHHELD,
            "resolved": resolved if isinstance(resolved, str) and LAYOUT.match(resolved)
            else WITHHELD}
    return kept


def _pattern(regex):
    return lambda value: value if isinstance(value, str) and regex.match(value) else WITHHELD


def _state(value):
    """A state keeps its closed prefix: `FAILED:<reason>` is `FAILED`."""
    if not isinstance(value, str):
        return WITHHELD
    head = value.split(":", 1)[0]
    return head if head in STATE_CODES else WITHHELD


def _count(value):
    return value if type(value) is int and value >= 0 else WITHHELD


def _count_or_none(value):
    return None if value is None else _count(value)


def _up_down(value):
    if not isinstance(value, dict):
        return WITHHELD
    return dict((key, _count(value.get(key))) for key in ("up", "down"))


def _codes(value):
    return [_code(v) for v in value] if isinstance(value, list) else WITHHELD


def _status(value):
    return value if value in STATE_CODES + ("NOT_STARTED", "CREATED", "unrecognized") \
        else WITHHELD


def _refusal(value):
    if not isinstance(value, dict):
        return WITHHELD
    return dict((key, _code(value.get(key)) if key != "rule" else
                 _pattern(re.compile(r"^R-[0-9]{3}$"))(value.get(key)))
                for key in ("type", "rule", "reason") if key in value)


# Every key a registry entry's `closed_output` may name, with its rule. A key a tool prints
# that its keep-list does not name is withheld, whatever it holds.
RULES = {
    "ok": _bool, "terminal": _bool,
    "failures": _failures, "wrote": _wrote, "outputs": _outputs,
    "missing": _missing, "resolved": _resolved,
    "template_version": _pattern(VERSION), "model": _pattern(MODEL),
    "job_id": _pattern(JOB_ID), "state": _state, "refusal": _refusal,
    # rnaseq_de.summary's aggregates, every key it prints (D5: "all").
    "command": _code, "assay": _code, "status": _status, "gate": _codes,
    "genes_tested": _count, "padj_lt_0.05": _up_down, "padj_lt_0.1": _count,
    "na_padj": _count, "samples_in_design": _count_or_none,
}
SUMMARY_KEYS = ["ok", "command", "assay", "status", "failures", "gate", "genes_tested",
                "padj_lt_0.05", "padj_lt_0.1", "na_padj", "samples_in_design"]

# The pilot log writer's lines, the only stdout its keep-list `*` lets through.
LINES = "*"
PILOT_LINES = [re.compile(p) for p in (
    r"^begin: span [0-9a-f]{16}; actor (?:human|agent)$",
    r"^end: span [0-9a-f]{16}; minutes [0-9]+\.[0-9]{2}$",
    r"^abort: span [0-9a-f]{16}$",
    r"^rows: [0-9]+; human: [0-9]+; agent: [0-9]+; tool: [0-9]+; open spans: [0-9]+; "
    r"nonce: ok$",
    r"^check failed: (?:open spans|no rows: [a-z0-9_]+)(?:; no rows: [a-z0-9_]+)*$",
    r"^import-tool: rows 2; wait_queue [0-9]+\.[0-9]{2}; compute [0-9]+\.[0-9]{2}$",
    r"^refused: [a-z_]+(?: line [0-9]+)?$")]


def pilot_lines(text):
    """(kept lines, withheld count) of the pilot log writer's output."""
    kept, withheld = [], 0
    for line in text.splitlines():
        if any(p.match(line) for p in PILOT_LINES):
            kept.append(line)
        else:
            withheld += 1
    return kept, withheld


def keep_list(tool_name):
    """The registry's `closed_output` list for a tool; a tool with none keeps nothing."""
    from tools.policy import registry
    for tool in registry():
        if tool["name"] == tool_name:
            return list(tool.get("closed_output", []))
    return []


def filter_value(keep, parsed):
    """The kept form of one parsed JSON object under a keep-list."""
    return dict((key, RULES[key](value) if key in keep else WITHHELD)
                for key, value in parsed.items())


def withheld_stderr(stderr):
    lines = len(stderr.splitlines())
    return "" if not lines else "%s; stderr lines: %d\n" % (WITHHELD, lines)


def filter_output(tool_name, stdout, stderr, exit_code, keep=None):
    """(stdout, stderr) as the agent may see them from a closed project."""
    keep = keep_list(tool_name) if keep is None else keep
    if keep == [LINES]:
        kept, withheld = pilot_lines(stdout)
        if withheld:
            kept.append("%s; stdout lines: %d" % (WITHHELD, withheld))
        return "".join(line + "\n" for line in kept), withheld_stderr(stderr)
    try:
        parsed = json.loads(stdout)
    except ValueError:
        parsed = None
    if not isinstance(parsed, dict):
        return (json.dumps({"withheld": True, "exit_code": exit_code}, sort_keys=True) + "\n",
                withheld_stderr(stderr))
    kept = filter_value([k for k in keep if k in RULES], parsed)
    return json.dumps(kept, indent=2, sort_keys=True) + "\n", withheld_stderr(stderr)


# --- when a call counts as closed (D5, M2) -----------------------------------------------------

class ClosedRefusal(ValueError):
    """A call refused before it runs; the code never quotes the path it refuses."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _raw_targets(project_dir):
    """The resolved targets of a project's 00_data/*/raw entries (D5: a raw link's target is
    the project's own data)."""
    try:
        entries = guard_hook._raw_entries(project_dir)
    except OSError:
        return []
    return [os.path.realpath(e) for e in entries if os.path.exists(e)]


def _path_like(token, bases):
    """A string is judged as a path when it holds a separator or names something that exists
    on either base; a bare word that names nothing (an assay, a type, a verb) is not a path."""
    if os.sep in token or "/" in token:
        return True
    return any(os.path.lexists(os.path.join(base, token)) for base in bases)


def closed_projects(workspace):
    """0107's closed projects, each extended with its raw-link targets: (name, label, forms)."""
    root = os.path.realpath(str(workspace))
    found = []
    for name, label, forms in guard_hook.closed_projects(root):
        found.append((name, label, list(forms) + _raw_targets(forms[0])))
    return found


def closed(path_args, workspace, cwd=None):
    """None when the call is open; the name of the one closed project whose output must be
    filtered; ClosedRefusal before running. Every string is judged, on both bases (the session
    cwd and the workspace root) and both forms (normalized and resolved), as the guard does."""
    root = os.path.realpath(str(workspace))
    projects = closed_projects(root)
    if not projects:
        return None
    bases = guard_hook._bases(str(cwd) if cwd else root, root)
    sources = guard_hook.declared_sources(root)[0]
    roots = [os.path.normpath(root), root]
    project_forms = dict((name, forms) for name, _, forms in projects)
    hits, loose = set(), []
    for token in path_args:
        if not isinstance(token, str) or not token or not _path_like(token, bases):
            continue
        if token.startswith("~"):
            raise ClosedRefusal("path_outside_workspace")
        forms = guard_hook._forms(token, bases)
        if sources and all(guard_hook.inside_declared(os.path.realpath(f), sources)
                           for f in forms):
            continue                      # D-iv: public data a human declared, not "outside"
        hit = guard_hook.closed_hit(token, root, bases, True, projects)
        if hit:
            hits.add(hit[1])
            # Inside that one project on every base and form: the project's own path.
            if hit[0] == "inside" and all(any(guard_hook._inside(form, f)
                                              for f in project_forms[hit[1]])
                                          for form in forms):
                continue
        if any(not any(guard_hook._inside(f, r) for r in roots) for f in forms):
            raise ClosedRefusal("path_outside_workspace")
        loose.append(token)
    if not hits:
        return None
    if len(hits) > 1 or loose:
        raise ClosedRefusal("path_outside_closed_project")
    return hits.pop()


# While a project is closed, the DE doors read their two path inputs only where the machine wrote
# them (step B review round 1, F-1): the stage 01 design and the 02.01 counts, both READ_ONLY to
# an agent. A file anywhere else in the project could be one the agent placed there, and the
# door's exit code or `ok` over it would answer a question about the project's samples.
FIXED_INPUTS = {
    "rnaseq_de.check": {"design": re.compile(r"^01_samplesheets/rnaseq_bulk_design\.csv$"),
                        "counts": re.compile(
                            r"^02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/run/results/"
                            r"(?:star_salmon|star_rsem|salmon)/"
                            r"salmon\.merged\.gene_counts_length_scaled\.tsv$")},
}
FIXED_INPUTS["rnaseq_de.prepare"] = FIXED_INPUTS["rnaseq_de.check"]


def fixed_inputs(tool_name, args, workspace, project):
    """ClosedRefusal("path_not_fixed_layout") unless each of the tool's fixed inputs, resolved
    from the workspace root where the dispatcher runs the tool, is the closed project's own
    fixed-layout file. Judged on the resolved form: that is the file the tool opens."""
    rules = FIXED_INPUTS.get(tool_name)
    if not rules:
        return
    root = os.path.realpath(str(workspace))
    home = os.path.realpath(os.path.join(root, "projects", project))
    for key in sorted(rules):
        value = args.get(key)
        if not isinstance(value, str) or not value:
            raise ClosedRefusal("path_not_fixed_layout")
        real = os.path.realpath(os.path.join(root, value))
        relative = os.path.relpath(real, home).replace(os.sep, "/")
        if relative.startswith("../") or not rules[key].match(relative):
            raise ClosedRefusal("path_not_fixed_layout")


def registration(tool, args, workspace, cwd=None):
    """True for 0107's declared registration (stage 00 on data a human declared public): the
    guard has judged every path of it, and its target is closed only for want of a dataset row
    (D-iv). Such a call is neither refused nor filtered here."""
    root = os.path.realpath(str(workspace))
    sources = guard_hook.declared_sources(root)[0]
    bases = guard_hook._bases(str(cwd) if cwd else root, root)
    return guard_hook.declared_registration(tool, args, root, bases,
                                            guard_hook.closed_projects(root), sources) is not None


def call_strings(value):
    """Every string in a dispatcher call's JSON, recursively (D-v: never a hand list of keys)."""
    return [s for _, s in guard_hook._strings(value)]


# --- bring_home's table, for outputs that never pass the dispatcher (D6) -----------------------

NUMBER = r"(?:uncomputable|nan|-?inf|Infinity|NaN|-?[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)"
# The reasons rerun_check.py records, cut to the text before the first `:`; a reason whose cut
# is not one of these is withheld whole. Bound to rerun_check.py's own literals by a drift test.
RERUN_REASONS = (
    "ambiguous tolerance entry", "cannot inspect GARS code", "cannot inspect pipeline code",
    "GARS code has uncommitted changes", "pipeline code has uncommitted changes",
    "dataset finalize failed", "dataset input basename collision", "dataset input unavailable",
    "dataset locations are not a recorded path list", "design check changed or missing",
    "design is not the canonical project design", "duplicate numeric column",
    "duplicate or empty numeric row", "empty numeric table", "execution config backend differs",
    "execution config drifted", "executor unavailable", "gars_commit differs from HEAD",
    "incomplete manifest", "input hash changed", "invalid or missing threshold",
    "invalid tolerance entries", "invalid tolerance entry", "invalid tolerance file",
    "manifest lacks required samplesheet input", "manifest_predates_expiry_recording",
    "no agreement_ref recorded", "no execution config recorded", "non-finite numeric cell",
    "non-numeric table cell", "numeric table missing header", "numeric table needs id column",
    "original output drifted", "output directory already exists", "output inventory differs",
    "output silently skipped", "output_hash", "pipeline_commit differs from HEAD",
    "ragged numeric table", "re-preparation config differs",
    "re-preparation execution config differs", "re-preparation inputs differ",
    "re-preparation params differ", "re-preparation pipeline differs", "re-run failed",
    "re-run status is not COMPLETE", "replay_dataset_mismatch", "run status is not COMPLETE",
    "runs must be positive", "second backend unavailable", "submit refused",
    "tolerance entry missing wrapper", "tolerance entry missing artifact",
    "tolerance entry missing cause", "tolerance entry missing evidence",
    "tolerances are not pre-committed", "unknown mode", "unknown or missing metric",
    "unrecognized output parameter", "unregistered wrapper", "wrapper collect failed",
    "wrapper prepare failed", "wrapper unavailable",
    "wrappers root override is only allowed for rerun-fixture")
# An artifact's path-kind: the OUTPUTS type a fixed wrapper path carries, never the path.
PATH_KINDS = (
    (re.compile(r"(?:^|/)run/tables/de_results\.csv$"), "de_results"),
    (re.compile(r"(?:^|/)run/tables/normalized_counts\.csv$"), "normalized_counts"),
    (re.compile(r"(?:^|/)adapted/counts_gene\.tsv$"), "counts_gene"),
    (re.compile(r"(?:^|/)adapted/gene_id_to_name\.tsv$"), "gene_id_map"),
    (re.compile(r"(?:^|/)salmon\.merged\.gene_counts(?:_length_scaled)?\.tsv$"), "counts_gene"),
    (re.compile(r"(?:^|/)salmon\.merged\.transcript_counts\.tsv$"), "counts_transcript"),
    (re.compile(r"(?:^|/)salmon\.merged\.gene_tpm\.tsv$"), "tpm_gene"),
    (re.compile(r"(?:^|/)run/report\.md$"), "report"),
    (re.compile(r"(?:^|/)run/figures/[a-z_]+\.png$"), "figure"),
)
BRING_HOME = {
    "rerun_console": [re.compile(p) for p in (
        r"^reproduction: [0-9]+/[0-9]+$",
        r"^graded [0-9]+ of [0-9]+ outputs$")],
    "rerun_artifact": re.compile(
        r"^(\S+) (byte_stable|numeric_tolerance) match=(yes|no) "
        r"(sha256_equal|max_absolute_error)=(" + NUMBER + r")$"),
    "rerun_failed": re.compile(r"^run ([0-9]+) match=no reason=(.*)$"),
    "manifest_check": [re.compile(p) for p in (
        r"^manifest completeness: [0-9]+/[0-9]+ required groups(?: \(uncomputable\))?$",
        r"^optional missing: (?:none|[0-9]+(?:,[0-9]+)*)$",
        r"^manifests read: [0-9]+; manifests graded: [0-9]+$")],
    "manifest_group": re.compile(
        r"^([0-9]+) (.+) (required|required_if_applicable|optional) "
        r"applicable=(?:yes|no) present=(?:yes|no)$"),
    "rerun_diff": [re.compile(p) for p in (
        r"^runs: [0-9]+$", r"^run [0-9]+$", r"^rows original/re-run: [0-9]+/[0-9]+$",
        r"^genes matched: [0-9]+$", r"^genes only in (?:original|re-run): [0-9]+$",
        r"^byte_equal: (?:yes|no)$", r"^max_abs_delta log2FoldChange: " + NUMBER + "$",
        r"^max_rel_delta padj: " + NUMBER + "$", r"^spearman log2FoldChange: " + NUMBER + "$",
        r"^crossings padj<0\.05 \(gained/lost\): [0-9]+/[0-9]+$", r"^sign flips: [0-9]+$",
        r"^na_padj original/re-run: [0-9]+/[0-9]+$",
        r"^na_log2FoldChange original/re-run: [0-9]+/[0-9]+$",
        r"^graded [0-9]+ of [0-9]+ rows$")],
}


def reason_prefix(reason):
    """A recorded reason cut to its closed prefix, or None when the cut is not a known one."""
    if not isinstance(reason, str):
        return None
    head = reason.split(":", 1)[0].strip()
    return head if head in RERUN_REASONS else None


def path_kind(path):
    for pattern, kind in PATH_KINDS:
        if isinstance(path, str) and pattern.search(path):
            return kind
    return "other"
