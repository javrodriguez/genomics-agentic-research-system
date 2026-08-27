#!/usr/bin/env bash
# Rebuild projects/_index.md from what is on disk.
#
# The index is GENERATED. Nothing reads it as authority: every column is derived from a file
# that is itself the authority (a project's CONTEXT.md, a sub-stage's STATUS). A hand-curated
# index drifts the moment a run finishes; a derived one cannot.
#
# Usage:  bash _system/build_projects_index.sh [workspace_root]
set -euo pipefail

WS="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PROJECTS="$WS/projects"
OUT="$PROJECTS/_index.md"

[ -d "$PROJECTS" ] || { echo "no projects/ under $WS" >&2; exit 1; }

{
    echo "# Projects"
    echo
    echo "**GENERATED — do not edit.** Rebuilt by \`_system/build_projects_index.sh\`."
    echo "Every column is derived; the authority is each project's \`CONTEXT.md\` and each"
    echo "sub-stage's \`STATUS\` file."
    echo
    echo "Last built: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "| Project | Template | Assay | Design | Samplesheet | Furthest sub-stage | State |"
    echo "|---|---|---|---|---|---|---|"

    found=0
    for p in "$PROJECTS"/*/; do
        [ -d "$p" ] || continue
        name=$(basename "$p")
        case "$name" in _*) continue ;; esac
        found=1

        version=$(sed -n 's/^| Template version | \(.*\) |$/\1/p' "$p/CONTEXT.md" 2>/dev/null | head -1)
        # An unsubstituted {{placeholder}} means stage 00's finalize never completed. Show it as
        # unknown rather than echoing the raw template text into the index.
        case "$version" in *"{{"*) version="?" ;; esac
        version="${version:-?}"

        # Portable on purpose: GNU find's -printf is absent on BSD/macOS, and under
        # `set -euo pipefail` its failure used to truncate the index mid-write.
        assays=$(for a in "$p/00_data"/*/; do [ -d "$a" ] && basename "$a"; done 2>/dev/null | sort)
        if [ -z "$assays" ]; then
            echo "| $name | $version | — | — | — | — | no assay directories |"
            continue
        fi

        while read -r assay; do
            [ -n "$assay" ] || continue

            # Design: does samples.csv have any experimental column filled?
            design="incomplete"
            s="$p/00_data/$assay/samples.csv"
            if [ -f "$s" ] && awk -F, 'NR>1 && ($2!="" || $3!="" || $4!="") {f=1} END{exit !f}' "$s"; then
                design="filled"
            fi
            [ -f "$s" ] || design="missing"

            sheet="no"
            [ -f "$p/01_samplesheets/${assay}_samplesheet.csv" ] && sheet="yes"

            # Furthest sub-stage: the last one in order with a STATUS, plus that STATUS.
            last="—"; state="NOT_STARTED"
            for d in "$p/02_bioinformatics/$assay"/*/; do
                [ -d "$d" ] || continue
                last=$(basename "$d")
                if [ -f "$d/STATUS" ]; then
                    state=$(awk 'NF{print $1; exit}' "$d/STATUS")
                else
                    state="NOT_STARTED"
                fi
            done

            echo "| $name | $version | $assay | $design | $sheet | $last | $state |"
        done <<< "$assays"
    done

    [ "$found" = 1 ] || echo "| _(none)_ | | | | | | |"
} > "$OUT"

echo "wrote $OUT"
