---
date: 2026-08-11
status: standing
kind: decision
symptoms:
  - "ModuleNotFoundError: No module named 'clawbio'"
  - "conda solve unsatisfiable (c-ares)"
touches:
  - gars/_references/environment.md
  - gars/_system/gars-env.sh
---
# Environment: two conda environments, skills installed rather than vendored

**Skills are installed, not vendored.** `clawbio` was missing entirely — both skill copies
import `clawbio.common.*` and could not even print `--help`. Installed from PyPI (0.6.1,
provenance verified against the repo URL in each SKILL.md) rather than vendored, because it
carries a real dependency tree (`opentelemetry`) and the wheel bundles duplicate copies of the
same skills.

**Two conda environments.** `nextflow` and `clawbio` cannot be solved together — conflicting
`c-ares` constraints via curl/libnghttp2. They are different runtimes and the wrapper calls
`nextflow` as a subprocess, so separation costs nothing.

**User-owned stack, not Lmod modules.** Apptainer 1.5.3 and Nextflow 26.04.6 are both *newer*
than the site modules and under our control. Verified the site's Singularity is not setuid and
user namespaces are enabled, so a user-owned rootless runtime has no privilege disadvantage.
`squashfuse` is required — without it Apptainer unpacks every multi-GB image on each container
launch.

**Always pin conda versions.** An unpinned `conda install nextflow` silently resolved to
**nextflow 0.24.2 (2017)** with openjdk 8, rather than reporting the conflict. It failed later
with opaque Maven TLS errors.
