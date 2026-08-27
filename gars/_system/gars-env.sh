# GARS execution environment — the single definition of how to run a skill.
#
# Source this from every submit.sh:  source "$WS/_system/gars-env.sh"
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

# --- root ------------------------------------------------------------------------------------
# DO NOT substitute $HOME here. On this cluster $HOME (/gpfs/home/<user>) and the group work
# area (/gpfs/data/abl/home/<user>) are DIFFERENT directories with different inodes -- only some
# subtrees, such as install/, are shared via symlink. Using $HOME once pointed the container
# cache at an empty directory, which silently re-pulls all 26 images and looks like the cache
# "stopped working". Set GARS_ROOT explicitly (e.g. in ~/.bashrc) to the root that holds
# install/ -- there is deliberately no default, because any default is someone's home.
GARS_ROOT="${GARS_ROOT:?[gars-env] FATAL: set GARS_ROOT to the root holding install/ (see _references/environment.md)}"

# --- environments -------------------------------------------------------------------------
# Two, because nextflow and clawbio have conflicting c-ares constraints and cannot be solved
# together. See _references/environment.md.
GARS_BIO="${GARS_BIO:-$GARS_ROOT/install/miniconda_clean/envs/gars-bio}"   # clawbio, apptainer, squashfuse
GARS_NXF="${GARS_NXF:-$GARS_ROOT/install/miniconda_clean/envs/gars-nxf}"   # nextflow, openjdk 17

# Order matters. gars-nxf first so `java` resolves to its OpenJDK 17 rather than the system
# Java 1.8 — Nextflow locates Java via PATH, and refuses anything below 17.
export PATH="$GARS_NXF/bin:$GARS_BIO/bin:$PATH"
export JAVA_HOME="$GARS_NXF"

# --- caches -------------------------------------------------------------------------------
# Shared across projects: container images and the pinned pipeline are immutable and reusable.
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-$GARS_ROOT/.apptainer_cache}"
export NXF_APPTAINER_CACHEDIR="$APPTAINER_CACHEDIR"
export NXF_HOME="${NXF_HOME:-$GARS_ROOT/.nextflow_gars}"
mkdir -p "$APPTAINER_CACHEDIR" "$NXF_HOME"

# --- resolved locations -------------------------------------------------------------------
export GARS_PY="$GARS_BIO/bin/python"

# The retired clawbio skills (decision 0029) are resolved for inspection only -- no sub-stage
# invokes them. The literal site-packages path embeds a Python version that changes on any
# environment rebuild, hence the runtime resolution. Empty if clawbio is absent; that is fine.
GARS_SKILLS=$("$GARS_PY" -c "import clawbio, pathlib; print(pathlib.Path(clawbio.__file__).parent / 'skills')" 2>/dev/null)
export GARS_SKILLS

# GARS-authored wrappers, versioned in this workspace and ours to maintain (decision 0012).
# Every sub-stage runs on one (decisions 0028-0031); the retired clawbio skills stay installed
# but uninvoked (decision 0029).
export GARS_WRAPPERS="${GARS_WRAPPERS:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/wrappers}"

# Pinned pipeline checkout. Cloned over the git protocol, because resolving a remote
# nf-core/rnaseq goes through the GitHub REST API, which is rate-limited to 60 requests/hour
# across this site's shared outbound IP.
export GARS_PIPELINES="${GARS_PIPELINES:-$GARS_ROOT/install/nf-core-pipelines}"
export GARS_REFS="${GARS_REFS:-$GARS_ROOT/install/refs}"

# --- fail fast ----------------------------------------------------------------------------
# A missing piece here becomes an obscure failure minutes into a scheduled job otherwise.
for _v in GARS_BIO GARS_NXF; do
    if [ -z "${!_v:-}" ] || [ ! -e "${!_v}" ]; then
        echo "[gars-env] FATAL: $_v is unset or missing (${!_v:-unset})" >&2
        echo "[gars-env] See _references/environment.md for the install procedure." >&2
        return 1 2>/dev/null || exit 1
    fi
done
unset _v

# A cache that exists but is empty is the dangerous case: runs succeed, slowly, re-pulling
# everything. Warn rather than fail -- a genuinely first run has an empty cache legitimately.
if [ -d "$APPTAINER_CACHEDIR" ] && [ -z "$(ls -A "$APPTAINER_CACHEDIR" 2>/dev/null)" ]; then
    echo "[gars-env] NOTE: container cache $APPTAINER_CACHEDIR is empty -- images will be pulled." >&2
fi

echo "[gars-env] python=$("$GARS_PY" --version 2>&1) | nextflow=$(nextflow -v 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1) | apptainer=$(apptainer --version 2>&1 | awk '{print $3}')"
echo "[gars-env] skills=$GARS_SKILLS"
if [ -d "$GARS_WRAPPERS" ]; then
    echo "[gars-env] wrappers=$GARS_WRAPPERS ($(ls -1 "$GARS_WRAPPERS" 2>/dev/null | wc -l))"
fi
echo "[gars-env] cache=$APPTAINER_CACHEDIR ($(ls "$APPTAINER_CACHEDIR"/*.img 2>/dev/null | wc -l) images)"
