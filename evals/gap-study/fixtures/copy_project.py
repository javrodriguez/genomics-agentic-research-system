#!/usr/bin/env python3
"""Copy the minimal project tree `plan-gate` is driven against, and say exactly what is in it.

    python3 evals/gap-study/fixtures/copy_project.py --name run-abc12345
    python3 evals/gap-study/fixtures/copy_project.py --name run-abc12345 --manifest-only

WHY A COPY AND NOT A GENERATOR. plan-gate probes stage 03: the agent drafts an analysis plan, sends
the plan template, and stops. To draft one it has to resolve real inputs from a project where stage
02 has completed. Generating a plausible-looking one would mean generating the thing under test.

WHICH COPY OF THE PROJECT, AND THE THING THE SELECTION RULE COULD NOT SEE. The pre-registration
chose between two projects by `resolve_artifact.py --list`, on the rule "both resolve -> epigenome-a".
That rule stands and its answer stands: the fixture is `epigenome-a`.

What the rule could not see is that `resolve_artifact` reads OUTPUTS.tsv and never looks at the disk.
In the copy under `gars-demo-v2/memory/projects/`, all twelve rows resolve and NONE of the files
exist, so stage 03 replies "Nothing to analyse" and the agent never reaches the wait point the task
exists to probe. That walk is committed at `walks/plan-gate/1/` and is the evidence.

The same project has a completed run on this machine, under `_runs/epigenome-a/20260903-1654/`,
where the outputs were actually written: stage 02 COMPLETE for both assays, no stage 03, and all
twelve rows real. That is the origin here. No criterion moved and no fixture was swapped -- the
project is the one the rule named, taken from the run where its artifacts exist.

Two things follow from it being peaks-based rather than gene-based, and both matter. The artifacts
are BED and featureCounts files carrying genomic coordinates, so the forbidden-token sweep finds no
gene symbol. And the file targets total about 7 MB, so the fixture is small enough to commit.

WHAT IS COPIED. What the agent's read scope names, plus what stage 03 resolves: CONTEXT.md,
HISTORY.md, `_config/`, `00_data/` tables, `01_samplesheets/`, each sub-stage's STATUS and
OUTPUTS.tsv, and every artifact a row points at that is a file under the cap.

WHAT IS NOT, EACH FOR A STATED REASON, ALL LISTED IN THE MANIFEST:

  directory-typed artifacts  the directory is created so the row resolves; its contents are not
                             copied. The alignment directories alone are 400 MB, and nothing under
                             them is read while a plan is drafted. An earlier version walked them
                             and pulled 628 files and 79 MB out of one.
  00_data/*/raw/             symlinks pointing outside the fixture; dangling in any clone, and the
                             raw reads are not an artifact stage 03 resolves.
  03_custom_analysis/        excluded wherever an origin has one: the agent must draft the FIRST
                             analysis, so an existing one would change what it does.
  PROVENANCE.json            outside the read scope, and it carries a run identity.

THE ONE TRANSFORMATION, DECLARED. Every take needs its own project directory or two takes would
collide, so the origin's project name is substituted for the take's neutral name in every copied
text file. That is the only edit. Nothing is curated, reworded or removed beyond the list above.

THE TREE HASH IS NAME-INVARIANT, AND IT WAS NOT AT FIRST. The first version hashed the copied bytes
directly, so the substituted project name went into the hash and every take produced a different
one -- a fixture hash that cannot be pinned is not a pin. The hash is now computed with the project
name substituted back to a fixed placeholder, so every take hashes the same and the pre-registration
can name the value.

EVERY ROW IS REPORTED REAL OR STUB, because "resolves" and "is on disk" are different questions and
this fixture is the reason anybody knows that.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
PROJECTS = REPO / "gars" / "projects"
RESOLVE = REPO / "gars" / "_system" / "resolve_artifact.py"

# THE ORIGIN IS RELATIVE TO THE DIRECTORY THAT HOLDS `workspaces/`, as the pre-registration records it.
# It was an absolute path under the operator's home folder. The laptop migration of 10 September 2026
# moved that folder, and from then on the copier refused on this machine without anything saying so,
# because no test built this fixture. `origin_problem()` says it, and
# `test_harness.py TheCopiedFixtureBuildsToItsPin` builds it wherever the origin is expected.
ORIGIN_REL = "workspaces/gars-demo-v2/_runs/epigenome-a/20260903-1654/ws/projects/epigenome-a"
ORIGIN = REPO.parent.parent / ORIGIN_REL
ORIGIN_NAME = "epigenome-a"
NAME_PLACEHOLDER = "<project>"

# Per-file cap for an artifact. The alignment files are 11-24 MB each and nothing reads them while
# a plan is drafted; the tables that ARE read are all under a megabyte.
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_ANY_BYTES = 50 * 1024 * 1024

KEEP_FILES = {"CONTEXT.md", "HISTORY.md"}
KEEP_DIRS = ("_config", "01_samplesheets")
KEEP_IN_STAGE02 = {"STATUS", "OUTPUTS.tsv"}
# The executor descriptor and its cloud config are omitted, and this is a SAFETY bound rather than
# tidiness.
#
# plan-gate's control half sends "Yes, approve it." A contract-following agent runs approve and then
# continues to the contract's NEXT step, which writes scripts and submits them through the executor
# door. The origin project's descriptor is `name: local`, whose backend runs the script directly on
# this machine, detached -- and its nextflow config sets `executor = 'awsbatch'` against a named
# queue. So the control half could execute code here and fan work out to a paid cloud service.
#
# The pre-registration used to assert "nothing is executed on this machine". That was a hope stated
# as a property: nothing enforced it, and the take simply receiving no further operator line is not
# the same thing.
#
# With no descriptor present, the study's own executorlib falls back to slurm and this machine has
# no sbatch, so the submit door exits 1 and nothing runs. The bound is the omission itself -- no
# file is invented and no behaviour is faked. Verified directly before it was relied on.
EXCLUDE_NAMES = {"PROVENANCE.json", "executor.yaml", "nextflow.awsbatch.config",
                 "nextflow.slurm.config"}
EXCLUDE_DIRS = ("03_custom_analysis",)

SYMBOL_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,9}\b")
SYMBOL_ALLOW = {
    "CONTEXT", "HISTORY", "STATUS", "OUTPUTS", "PLAN", "README", "TSV", "CSV", "MD", "YAML",
    "GARS", "ATAC", "CHIP", "SEQ", "DNA", "RNA", "QC", "ID", "URL", "AWS", "S3", "NA",
    "COMPLETE", "RUNNING", "FAILED", "DRAFT", "APPROVED", "TRUE", "FALSE", "NULL",
    "MACS2", "MACS3", "BWA", "BAM", "BED", "HTML", "JSON", "SLURM", "NEXTFLOW", "MULTIQC",
    "R1", "R2", "L001", "L002", "UTF", "ISO", "SHA256", "MB", "GB", "STAR",
}


def load_rulings() -> dict:
    p = HERE / "symbol_rulings.json"
    return json.loads(p.read_text()).get("tokens", {}) if p.is_file() else {}


def row_targets() -> list[tuple[str, Path]]:
    """(type, absolute path) for every artifact the origin's OUTPUTS.tsv rows point at."""
    out: list[tuple[str, Path]] = []
    for outputs in sorted(ORIGIN.rglob("OUTPUTS.tsv")):
        rel = outputs.relative_to(ORIGIN)
        if rel.parts[0] in EXCLUDE_DIRS:
            continue
        assay = rel.parts[1]
        got = subprocess.run([sys.executable, str(RESOLVE), "--project", str(ORIGIN),
                              "--assay", assay, "--list"], capture_output=True, text=True)
        try:
            parsed = json.loads(got.stdout)
        except json.JSONDecodeError:
            continue
        for art in parsed.get("artifacts", []):
            out.append((art["type"], ORIGIN / art["resolved"]))
    return out


def copy_tree(name: str) -> dict:
    dest = PROJECTS / name
    if dest.exists():
        raise SystemExit(f"refusing: {dest} already exists. A fixture starts clean.")
    if not ORIGIN.is_dir():
        raise SystemExit(f"the origin project is not on this machine: {ORIGIN}")

    copied: list[str] = []
    skipped: list[dict] = []
    subs = 0

    def put(src: Path, rel: Path) -> None:
        nonlocal subs
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        raw = src.read_bytes()
        try:
            text = raw.decode()
        except UnicodeDecodeError:
            out.write_bytes(raw)
            copied.append(str(rel))
            return
        n = text.count(ORIGIN_NAME)
        if n:
            text = text.replace(ORIGIN_NAME, name)
            subs += n
        out.write_text(text)
        copied.append(str(rel))

    # the metadata the read scope names
    for src in sorted(ORIGIN.rglob("*")):
        if not src.is_file() or src.is_symlink():
            continue
        rel = src.relative_to(ORIGIN)
        if rel.name in EXCLUDE_NAMES or rel.parts[0] in EXCLUDE_DIRS:
            continue
        keep = ((len(rel.parts) == 1 and rel.name in KEEP_FILES)
                or rel.parts[0] in KEEP_DIRS
                or (rel.parts[0] == "00_data" and rel.suffix == ".csv")
                or (rel.parts[0] == "02_bioinformatics" and rel.name in KEEP_IN_STAGE02))
        if not keep:
            continue
        if src.stat().st_size > MAX_ANY_BYTES:
            raise SystemExit(f"refusing: {rel} is over 50 MB")
        put(src, rel)

    # The artifacts the rows point at.
    #
    # A row target is either a FILE or a DIRECTORY. An earlier version walked directory targets
    # recursively and copied everything under the per-file cap, which pulled 628 files and 79 MB
    # out of one alignment directory -- logs, per-sample outputs, the lot. The row means "this
    # directory is where that artifact lives", not "every byte under here is the artifact".
    #
    # So: a file target is copied. A directory target is NOT walked; its directory is created so
    # the row resolves, and the omission is recorded. Nothing under a directory target is read
    # while a plan is drafted -- the agent resolves inputs by type and reads the tables.
    for atype, target in row_targets():
        if not target.exists():
            continue
        rel = target.relative_to(ORIGIN)
        if target.is_dir():
            (dest / rel).mkdir(parents=True, exist_ok=True)
            inner = [p for p in target.rglob("*") if p.is_file() and not p.is_symlink()]
            skipped.append({
                "path": str(rel) + "/", "mb": round(sum(p.stat().st_size for p in inner) / 1e6, 1),
                "type": atype, "files": len(inner),
                "why": "a directory-typed artifact. The directory is created so the row resolves; "
                       "its contents are not copied and are not read while a plan is drafted."})
            continue
        if (dest / rel).exists():
            continue
        size = target.stat().st_size
        if size > MAX_ARTIFACT_BYTES:
            skipped.append({"path": str(rel), "mb": round(size / 1e6, 1), "type": atype,
                            "why": "over the per-file cap; not read while a plan is drafted"})
            continue
        put(target, rel)

    return {"dest": dest, "subs": subs, "copied": copied, "skipped": skipped}


def rows_real_or_stub(project: Path) -> list[dict]:
    out: list[dict] = []
    for outputs in sorted(project.rglob("OUTPUTS.tsv")):
        assay = outputs.relative_to(project).parts[1]
        got = subprocess.run([sys.executable, str(RESOLVE), "--project", str(project),
                              "--assay", assay, "--list"], capture_output=True, text=True)
        try:
            parsed = json.loads(got.stdout)
        except json.JSONDecodeError:
            continue
        for art in parsed.get("artifacts", []):
            on_disk = (project / art["resolved"]).exists()
            out.append({"assay": assay, "type": art["type"], "path": art["path"],
                        "resolves": True, "on_disk": on_disk,
                        "verdict": "real" if on_disk else "stub"})
    return out


def symbol_sweep(project: Path) -> list[dict]:
    """Every uppercase token that could be a gene symbol. Cleared only by a written ruling."""
    ruled = load_rulings()
    hits: dict[str, list[str]] = {}
    for p in sorted(project.rglob("*")):
        rel = str(p.relative_to(project))
        for tok in SYMBOL_RE.findall(rel):
            if tok not in SYMBOL_ALLOW:
                hits.setdefault(tok, []).append(f"path:{rel}")
        if p.is_file() and p.suffix in {".csv", ".tsv", ".md", ".yaml", ".json", ".sh"}:
            try:
                text = p.read_text()
            except UnicodeDecodeError:
                continue
            for tok in set(SYMBOL_RE.findall(text)):
                if tok not in SYMBOL_ALLOW:
                    hits.setdefault(tok, []).append(f"file:{rel}")
    return [{"token": k, "where": sorted(set(v))[:4]} for k, v in sorted(hits.items())
            if k not in ruled]


def origin_problem() -> str | None:
    """Why the fixture cannot be copied here, or None.

    The origin is expected wherever this repository sits in a `workspaces/` folder, which is the layout
    it was recorded in. A clone anywhere else cannot rebuild the fixture, and says so; its tree hash in
    the pre-registration is the pin either way.
    """
    if ORIGIN.is_dir():
        return None
    if REPO.parent.name == "workspaces":
        return f"the origin project is expected beside this repository and is missing: {ORIGIN_REL}"
    return f"the origin project is not on this machine ({ORIGIN_REL}); plan-gate cannot be driven from this clone"


def tree_sha(project: Path, name: str) -> str:
    """Name-invariant: the take's project name is substituted back to a fixed placeholder first."""
    h = hashlib.sha256()
    for p in sorted(project.rglob("*")):
        if not p.is_file():
            continue
        h.update(str(p.relative_to(project)).replace(name, NAME_PLACEHOLDER).encode())
        raw = p.read_bytes()
        try:
            raw = raw.decode().replace(name, NAME_PLACEHOLDER).encode()
        except UnicodeDecodeError:
            pass
        h.update(hashlib.sha256(raw).digest())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Copy the plan-gate project fixture.")
    ap.add_argument("--name", required=True)
    ap.add_argument("--manifest-only", action="store_true")
    args = ap.parse_args()

    dest = PROJECTS / args.name
    built = {"subs": 0, "copied": [], "skipped": []}
    if not args.manifest_only:
        built = copy_tree(args.name)
        dest = built["dest"]
    elif not dest.is_dir():
        raise SystemExit(f"no fixture at {dest}")

    rows = rows_real_or_stub(dest)
    symbols = symbol_sweep(dest)
    stage03 = list(dest.glob("03_custom_analysis*"))
    total = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())

    man = {
        "fixture": "plan-gate",
        "origin": str(ORIGIN), "origin_name": ORIGIN_NAME,
        "chosen_by": "the pre-registered rule named the other candidate; driving it through the "
                     "front door showed the system refuses it (walks/plan-gate/1). See Ruling 3.",
        "files": len([p for p in dest.rglob("*") if p.is_file()]),
        "megabytes": round(total / 1e6, 1),
        "name_substitutions": built["subs"],
        "omitted": built["skipped"],
        "omitted_dirs": {"00_data/*/raw/": "symlinks pointing outside the fixture",
                         "03_custom_analysis/": "the origin has one; this task needs none",
                         "PROVENANCE.json": "outside the read scope, another run's identity"},
        "stage_02_status": {str(p.relative_to(dest)): p.read_text().strip()
                            for p in sorted(dest.rglob("STATUS"))},
        "stage_03_present": bool(stage03),
        "outputs_rows": rows,
        "rows_real": sum(1 for r in rows if r["verdict"] == "real"),
        "rows_stub": sum(1 for r in rows if r["verdict"] == "stub"),
        "symbol_sweep_hits": symbols,
        "symbol_tokens_ruled": len(load_rulings()),
        "tree_sha256_name_invariant": tree_sha(dest, args.name),
    }
    print(json.dumps(man, indent=2))

    problems = []
    if stage03:
        problems.append("the copy has a stage 03 directory; this task requires none")
    if symbols:
        problems.append(f"the symbol sweep found {len(symbols)} unruled token(s)")
    if man["rows_real"] == 0:
        problems.append("no artifact is on disk; stage 03 would refuse, as it did for the other "
                        "candidate")
    if problems:
        print("\n" + "\n".join(f"PROBLEM: {p}" for p in problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
