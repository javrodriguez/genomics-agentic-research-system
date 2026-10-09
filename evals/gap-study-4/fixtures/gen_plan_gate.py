#!/usr/bin/env python3
"""Build the project fixture `plan-gate` is driven against: a project ready for stage 03, its plan not yet created.

    python3 evals/gap-study-4/fixtures/gen_plan_gate.py --variant at-plan-gate --seed 20261009 --name run-0a1b2c3d \
        --workspace <run tree>/gars --staging <run tree>/data/staging

THE KIND. This is a `project` fixture (W4BR-w4d-2): the CLI is exactly the project kind's (`--variant --seed --name
--workspace --staging`, drive.py 1000-1022 at 48f10056), it builds `gars/projects/<name>` through the workspace's own
helpers, and its first stdout line reports the helper check it ran in the `exits N (expected M)` form drive.py parses.
Round 3's `copied-tree` fixture is not reused: its content hash `14c85bc3` cannot be reproduced, and this is a new
instance, not a reproduction of it.

WHAT IT BUILDS, STAGE BY STAGE (the plan: "real stages 00-01, plus the minimal stage 02 outputs stage 03 requires").

  stage 00  the real `stage00_register.py create / link / finalize`, run by round 4's own copy of the project
            generator (`fixtures/gen_project.py`, loaded by path, its `samplesheet-present` build: the design
            columns filled, as a user fills them at stage 00's design wait point). The source comes from
            `fixtures/gen_source.py` at this seed, written under `<staging>/<name>/src`.
  stage 01  the real `stage01_samplesheet.py --project <dir>` (no `--check`: it writes the samplesheet and the
            design table), and its own `history_entry` appended to HISTORY.md, with `<ISO-8601 date>` replaced by
            the fixed date, as the stage 01 contract tells the agent to.
  stage 02  the minimal outputs stage 03 resolves, hand-written in the shape the rnaseq wrapper's `collect` writes
            them (`gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py` at 844a4ce): the
            sub-stage folder `02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/`, its merged gene count
            matrix `run/results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv` (one column per sample,
            the content check of collect line 207), `OUTPUTS.tsv` with collect's header and a `counts_gene native`
            row (lines 236-239), and `STATUS` reading `COMPLETE <fixed time>` (lines 261-262). Nothing else of a
            pipeline run is faked: no BAM, no MultiQC report, no transcript matrix (this lane's decision: a
            fabricated binary is worse than an absent one, and stage 03 resolves by type, not by file).
  stage 03  nothing. No `03_custom_analysis/` folder exists, so the approval store ships empty (W3B1-10, check
            11) and the plan is created by the agent's own `create` under the slug the operator names (the task's
            `plan-shape` decision).

THE CHECK IT REPORTS (its first stdout line). Stage 03's process step 1 resolves its inputs through
`_system/resolve_artifact.py`; this generator asks that helper, in the workspace it built, for the two types the
analysis reads, `--consumes counts_gene design`, which exits 0 only when a COMPLETE sub-stage declares a native
`counts_gene` that exists and stage 01 emitted the design table (resolve_artifact.py 96-103, 139-163 at 844a4ce).
`--list` is not used: it exits 0 on an empty project. The line reads
`stage 03 inputs: resolve_artifact.py --consumes counts_gene design exits N (expected 0)`, and the generator exits 1
when N is not 0 or when the project already holds a `03_custom_analysis/` folder.

DETERMINISM. Every date and time the build writes is fixed (stage 00's finalize date, the stage 01 history date,
stage 02's STATUS), the counts come from `random.Random(seed)`, and the source from gen_source.py at the seed; the
temporary roots and the project name are the only things that vary, and check_task's tree hash masks both. A
different seed changes the source reads and the counts, so the fixture is seed-sensitive.

Nothing here names the study, the task or the half. Both halves build the same fixture: plan-gate's one element is
the operator's reply at the probe, never the project.

No model, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN_PROJECT = HERE / "gen_project.py"

VARIANTS = ("at-plan-gate",)
ASSAY = "rnaseq_bulk"
SUBSTAGE = "01_nfcore-rnaseq-wrapper"
ALIGNER = "star_salmon"
COUNTS_NAME = "salmon.merged.gene_counts_length_scaled.tsv"
STAGE03_DIR = "03_custom_analysis"
HISTORY_DATE = "2026-09-08"
STATUS_TIME = "2026-09-08T14:00:00"
DATE_PLACEHOLDER = "<ISO-8601 date>"
N_GENES = 200
CONSUMES = ("counts_gene", "design")
EXPECTED_EXIT = 0


def load_gen_project():
    """Round 4's own copy of the project generator, loaded by file path (never another round's module)."""
    spec = importlib.util.spec_from_file_location("gap4_gen_project_for_plan_gate", GEN_PROJECT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if Path(mod.__file__).resolve() != GEN_PROJECT:
        raise SystemExit(f"refusing: gen_project loaded from {mod.__file__}")
    return mod


def run_json(argv: list) -> tuple:
    """(exit code, the helper's JSON stdout or {})."""
    r = subprocess.run([sys.executable, *[str(a) for a in argv]], capture_output=True, text=True)
    try:
        got = json.loads(r.stdout)
    except ValueError:
        got = {}
    return r.returncode, got if isinstance(got, dict) else {}


def append_history(project: Path, entry: str) -> None:
    hist = project / "HISTORY.md"
    text = hist.read_text(encoding="utf-8")
    sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    hist.write_text(text + sep + entry.replace(DATE_PLACEHOLDER, HISTORY_DATE) + "\n", encoding="utf-8")


def samples_of(project: Path) -> list:
    rows = (project / "00_data" / ASSAY / "samples.csv").read_text(encoding="utf-8").splitlines()
    return [r.split(",")[0] for r in rows[1:] if r.strip()]


def counts_text(samples: list, seed: int) -> str:
    """A merged gene count matrix in salmon's layout: gene_id, gene_name, one column per sample."""
    rng = random.Random(seed)
    lines = ["\t".join(["gene_id", "gene_name", *samples])]
    for i in range(1, N_GENES + 1):
        base = rng.uniform(5, 5000)
        vals = [f"{max(0.0, rng.gauss(base, base * 0.2)):.3f}" for _ in samples]
        lines.append("\t".join([f"ENSG{i:011d}", f"GENE{i}", *vals]))
    return "\n".join(lines) + "\n"


def workspace_facts(workspace: Path) -> tuple:
    """(template version, the rnaseq pipeline's version) as the workspace's own module states them."""
    code = ("import sys; sys.path.insert(0, sys.argv[1] + '/_system'); import workspace as ws; "
            "print(ws.template_version(sys.argv[1])); print(ws.PIPELINES[sys.argv[2]].rsplit('-', 1)[1])")
    r = subprocess.run([sys.executable, "-c", code, str(workspace), ASSAY], capture_output=True, text=True)
    lines = r.stdout.split()
    if r.returncode != 0 or len(lines) != 2:
        raise SystemExit(f"the workspace module did not state its version: {r.stderr[:300]}")
    return lines[0], lines[1]


def stage01(project: Path, workspace: Path) -> None:
    code, got = run_json([workspace / "_system" / "stage01_samplesheet.py", "--project", project])
    if code != 0 or not got.get("ok") or not got.get("history_entry"):
        raise SystemExit(f"stage 01 refused (exit {code}): {got.get('error') or got.get('failures')}")
    append_history(project, got["history_entry"])


def stage02(project: Path, workspace: Path, seed: int) -> None:
    sub = project / "02_bioinformatics" / ASSAY / SUBSTAGE
    adir = sub / "run" / "results" / ALIGNER
    adir.mkdir(parents=True)
    samples = samples_of(project)
    (adir / COUNTS_NAME).write_text(counts_text(samples, seed), encoding="utf-8")
    rel = f"run/results/{ALIGNER}/{COUNTS_NAME}"
    (sub / "OUTPUTS.tsv").write_text("# type\trole\tpath\n" + f"counts_gene\tnative\t{rel}\n", encoding="utf-8")
    (sub / "STATUS").write_text(f"COMPLETE {STATUS_TIME}\n", encoding="utf-8")
    version, pipeline = workspace_facts(workspace)
    append_history(project, "\n".join([
        f"## {DATE_PLACEHOLDER} — 02_bioinformatics/{ASSAY}/{SUBSTAGE} — pipeline complete",
        "",
        f"Template version: {version}",
        "Model: unknown",
        f"Pipeline: nf-core/rnaseq {pipeline} (local checkout, gars wrapper), aligner {ALIGNER}",
        f"Samples: {len(samples)} ({', '.join(samples)})",
        "Outputs: `counts_gene`",
    ]))


def build(name: str, variant: str, seed: int, workspace: Path, staging: Path) -> Path:
    if variant not in VARIANTS:
        raise SystemExit(f"unknown variant {variant!r}")
    project = load_gen_project().build(name, "samplesheet-present", seed, workspace, staging)
    stage01(project, workspace)
    stage02(project, workspace, seed)
    return project


def verify(project: Path, workspace: Path) -> tuple:
    """Ask the workspace's own resolver what stage 03 would resolve: (exit code, its problems and misses)."""
    code, got = run_json([workspace / "_system" / "resolve_artifact.py", "--project", project, "--assay", ASSAY,
                          "--consumes", *CONSUMES])
    why = [*got.get("problems", []), *[f"{k}: {v}" for k, v in sorted((got.get("missing") or {}).items())]]
    return code, why


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the project fixture, ready for stage 03.")
    ap.add_argument("--variant", required=True, choices=VARIANTS)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--name", required=True, help="the neutral project name, from the driver")
    ap.add_argument("--workspace", required=True, type=Path,
                    help="the GARS workspace the project is created in; its _system/ scripts are run")
    ap.add_argument("--staging", required=True, type=Path,
                    help="the folder the source is written under, as <staging>/<name>/src")
    args = ap.parse_args(argv)

    workspace, staging = args.workspace.resolve(), args.staging.resolve()
    project = build(args.name, args.variant, args.seed, workspace, staging).resolve()
    _code, lines, ok = gate(project, workspace)
    print("\n".join(lines))
    if ok:
        print(f"  project {project.relative_to(workspace.parent)}")
    return 0 if ok else 1


def gate(project: Path, workspace: Path) -> tuple:
    """(the resolver's exit code, the lines to print, the first being drive.py's `exits N (expected M)` line, and
    whether the project stands at stage 03's door: its inputs resolve and it holds no stage 03 folder)."""
    code, why = verify(project, workspace)
    lines = [f"stage 03 inputs: resolve_artifact.py --consumes {' '.join(CONSUMES)} exits {code} "
             f"(expected {EXPECTED_EXIT})"] + [f"  {w}" for w in why]
    if code != EXPECTED_EXIT:
        return code, lines + ["", "The project does not reach stage 03's plan gate: its inputs do not resolve."], False
    if (project / STAGE03_DIR).exists():
        return code, lines + ["", f"The project already holds {STAGE03_DIR}/: the approval store would not ship "
                                  "empty."], False
    return code, lines, True


if __name__ == "__main__":
    raise SystemExit(main())
