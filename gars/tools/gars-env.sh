# GARS execution environment — the single definition of how to run a skill.
#
# Source this from every submit.sh:  source "$WS/tools/gars-env.sh"
#
# Why this file exists: the same ~10 lines of setup were previously copy-pasted into every
# submit.sh, in every project, for every sub-stage. They drifted — a salvaged script was found
# still referencing a vendored skills path that no longer existed.
#
# Why absolute paths rather than `conda activate`: activation would work, but stacking two
# environments needs conda's shell hook sourced inside every batch script, which is more moving
# parts and fails differently on nodes where the hook is absent. Absolute paths behave
# identically everywhere, which is what a Slurm script needs.
#
# Why this lives in the workspace and not in $HOME: a workspace is a copy of the template and
# the contracts treat it as self-contained, so copying a workspace carries its environment
# definition. It is versioned in git, so a change is a reviewable commit rather than an
# untracked edit to a home-directory script.

# --- environments -------------------------------------------------------------------------
# Two, because nextflow and clawbio have conflicting c-ares constraints and cannot be solved
# together. See docs/environment.md.
GARS_BIO="${GARS_BIO:-$HOME/install/miniconda_clean/envs/gars-bio}"   # clawbio, apptainer, squashfuse
GARS_NXF="${GARS_NXF:-$HOME/install/miniconda_clean/envs/gars-nxf}"   # nextflow, openjdk 17

# Order matters. gars-nxf first so `java` resolves to its OpenJDK 17 rather than the system
# Java 1.8 — Nextflow locates Java via PATH, and refuses anything below 17.
export PATH="$GARS_NXF/bin:$GARS_BIO/bin:$PATH"
export JAVA_HOME="$GARS_NXF"

# --- caches -------------------------------------------------------------------------------
# Shared across projects: container images and the pinned pipeline are immutable and reusable.
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-$HOME/.apptainer_cache}"
export NXF_APPTAINER_CACHEDIR="$APPTAINER_CACHEDIR"
export NXF_HOME="${NXF_HOME:-$HOME/.nextflow_gars}"
mkdir -p "$APPTAINER_CACHEDIR" "$NXF_HOME"

# --- resolved locations -------------------------------------------------------------------
export GARS_PY="$GARS_BIO/bin/python"

# Skills are never vendored. Resolve them from the installed clawbio package: the literal
# site-packages path embeds a Python version that changes on any environment rebuild.
GARS_SKILLS=$("$GARS_PY" -c "import clawbio, pathlib; print(pathlib.Path(clawbio.__file__).parent / 'skills')" 2>/dev/null)
export GARS_SKILLS

# Pinned pipeline checkout. Cloned over the git protocol, because resolving a remote
# nf-core/rnaseq goes through the GitHub REST API, which is rate-limited to 60 requests/hour
# across this site's shared outbound IP.
export GARS_PIPELINES="${GARS_PIPELINES:-$HOME/install/nf-core-pipelines}"
export GARS_REFS="${GARS_REFS:-$HOME/install/refs}"

# --- fail fast ----------------------------------------------------------------------------
# A missing piece here becomes an obscure failure minutes into a scheduled job otherwise.
for _v in GARS_BIO GARS_NXF GARS_SKILLS; do
    if [ -z "${!_v:-}" ] || [ ! -e "${!_v}" ]; then
        echo "[gars-env] FATAL: $_v is unset or missing (${!_v:-unset})" >&2
        echo "[gars-env] See docs/environment.md for the install procedure." >&2
        return 1 2>/dev/null || exit 1
    fi
done
unset _v

echo "[gars-env] python=$("$GARS_PY" --version 2>&1) | nextflow=$(nextflow -v 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1) | apptainer=$(apptainer --version 2>&1 | awk '{print $3}')"
echo "[gars-env] skills=$GARS_SKILLS"
