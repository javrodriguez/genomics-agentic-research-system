#!/usr/bin/env bash
# Re-run the pipelines of a GARS reproduction package on this machine:
#
#   bash rerun.sh --out <empty folder>
#
# It needs Docker (with at least 4 CPUs and about 16 GB of memory available to it), Java, curl,
# python3 and the Nextflow launcher (`nextflow`) on PATH; no GARS install and no account.
# Before Nextflow starts it downloads every input and reference file from the URL the package
# names and refuses on any checksum mismatch, saying which file and where that checksum came from.
# Each stage 02 pipeline then runs as
#   nextflow run <pipeline> -r <pipeline commit> -params-file <params> -c env/rerun.config -profile docker
# A stage 03 analysis is packaged in full, but its re-run is not automated in this version.
# Afterwards: python3 verify.py --against <that folder>.
# Exit codes: 0 done, 1 a step failed, 2 refused before any pipeline ran, 3 usage.
set -euo pipefail

PACKAGE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT=""
MIN_CPUS=4
MIN_MEMORY_BYTES=15000000000   # about 16 GB of machine; the run's clamp is 14 GB (env/rerun.config)

usage() {
    echo "usage: bash rerun.sh --out <empty folder>" >&2
    exit 3
}

refuse() {
    echo "rerun refused: $*" >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --out)
            [ "$#" -ge 2 ] || usage
            OUT="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '2,14p' "$0"
            exit 0
            ;;
        *)
            usage
            ;;
    esac
done
[ -n "$OUT" ] || usage

for tool in docker java curl python3 nextflow; do
    command -v "$tool" >/dev/null 2>&1 || refuse "$tool is not on PATH"
done
if [ -e "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ]; then
    refuse "$OUT is not empty"
fi
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

# The machine: what Docker itself can use, since every process runs in a container.
read -r NCPU MEMORY < <(docker info --format '{{.NCPU}} {{.MemTotal}}' 2>/dev/null) \
    || refuse "docker info failed; is the Docker daemon running?"
[ "${NCPU:-0}" -ge "$MIN_CPUS" ] \
    || refuse "Docker has ${NCPU:-0} CPUs; the run's task sizes need $MIN_CPUS (env/rerun.config)"
[ "${MEMORY:-0}" -ge "$MIN_MEMORY_BYTES" ] \
    || refuse "Docker has ${MEMORY:-0} bytes of memory; the run's task sizes need about 16 GB (env/rerun.config)"

# Every input and reference file: download, then check against the package's checksum.
python3 - "$PACKAGE" "$OUT" <<'PY' || exit 2
import csv, hashlib, io, os, subprocess, sys
package, out = sys.argv[1], sys.argv[2]
def rows(rel):
    with io.open(os.path.join(package, rel), encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))
wanted = {}
for rel, folder in (('inputs/inputs.tsv', 'inputs'), ('inputs/reference.tsv', 'refs')):
    for row in rows(rel):
        dest = os.path.join(out, folder, row['file'])
        known = wanted.get(dest)
        if known and known[1] != row['sha256']:
            sys.exit('rerun refused: %s is listed twice with different checksums' % row['file'])
        wanted[dest] = (row['url'], row['sha256'], row['sha256_source'])
for dest, (url, expected, label) in sorted(wanted.items()):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print('download %s' % os.path.relpath(dest, out), flush=True)
    if subprocess.call(['curl', '-fsSL', '--retry', '3', '-o', dest, url]) != 0:
        sys.exit('rerun refused: could not download %s from %s' % (os.path.basename(dest), url))
    digest = hashlib.sha256()
    with open(dest, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        sys.exit('rerun refused: %s has sha256 %s, not %s (%s); no pipeline was started'
                 % (os.path.basename(dest), digest.hexdigest(), expected, label))
PY

# The samplesheets and parameters, with this machine's folders in place of the package's names.
python3 - "$PACKAGE" "$OUT" <<'PY' || exit 2
import csv, io, json, os, sys
package, out = sys.argv[1], sys.argv[2]
with io.open(os.path.join(package, 'code', 'pipelines.tsv'), encoding='utf-8', newline='') as handle:
    stages = [row['stage'] for row in csv.DictReader(handle, delimiter='\t')]
os.makedirs(os.path.join(out, 'params'), exist_ok=True)
for stage in stages:
    with io.open(os.path.join(package, 'inputs', stage + '.samplesheet.csv'), encoding='utf-8') as handle:
        sheet = handle.read().replace('<INPUTS>/', os.path.join(out, 'inputs') + '/')
    with io.open(os.path.join(out, 'inputs', stage + '.samplesheet.csv'), 'w', encoding='utf-8') as handle:
        handle.write(sheet)
    with io.open(os.path.join(package, 'params', stage + '.params.json'), encoding='utf-8') as handle:
        params = json.load(handle)
    params = dict((k, v.replace('<RERUN>', out) if isinstance(v, str) else v) for k, v in params.items())
    with io.open(os.path.join(out, 'params', stage + '.params.json'), 'w', encoding='utf-8') as handle:
        json.dump(params, handle, indent=2, sort_keys=True)
PY

status=0
while IFS=$'\t' read -r stage pipeline commit nxf parser; do
    echo "stage $stage: $pipeline at $commit, Nextflow $nxf"
    mkdir -p "$OUT/launch/$stage" "$OUT/logs"
    (
        cd "$OUT/launch/$stage"
        export NXF_VER="$nxf"
        if [ "$parser" != "none" ]; then export NXF_SYNTAX_PARSER="$parser"; fi
        nextflow run "$pipeline" -r "$commit" \
            -params-file "$OUT/params/$stage.params.json" \
            -c "$PACKAGE/env/rerun.config" \
            -profile docker \
            -work-dir "$OUT/work/$stage"
    ) > "$OUT/logs/$stage.log" 2>&1 || { echo "stage $stage failed; see $OUT/logs/$stage.log" >&2; status=1; }
done < <(python3 - "$PACKAGE" <<'PY'
import csv, io, os, sys
with io.open(os.path.join(sys.argv[1], 'code', 'pipelines.tsv'), encoding='utf-8', newline='') as handle:
    for row in csv.DictReader(handle, delimiter='\t'):
        print('\t'.join((row['stage'], row['pipeline'], row['pipeline_commit'], row['nextflow'],
                         row['nxf_syntax_parser'])))
PY
)

if [ -f "$PACKAGE/params/approval.tsv" ]; then
    echo "A stage 03 analysis is in this package (params/approval.tsv); its re-run is not automated in this version."
fi
[ "$status" -eq 0 ] || exit 1
echo "re-run complete; now: python3 \"$PACKAGE/verify.py\" --against \"$OUT\""
