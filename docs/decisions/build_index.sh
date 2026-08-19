#!/usr/bin/env bash
# Rebuild docs/decisions/CONTEXT.md's index table from each decision's frontmatter.
# The table is GENERATED. Edit the decision files, then re-run this.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

{
    cat <<'HEAD'
# Decision log

One decision per file, append-only. A decision records **what was decided and why**, because the
reasoning is the part that gets lost and then reversed by someone who sees a simpler-looking
option. Status and backlog live in [DEVELOPMENT.md](../../DEVELOPMENT.md); nothing volatile
belongs here.

## Conventions

| Rule | Detail |
|---|---|
| Filename | `NNNN-kebab-slug.md`, number assigned in order, never reused |
| Frontmatter | `date`, `status` (`standing` / `superseded`), `touches` (paths this decision constrains) |
| Superseding | Never edit a decision to reverse it. Write a new one and set the old to `status: superseded`, naming its replacement. |
| `touches` | The files a reader must not change without reading this first. Keep it accurate — it is what makes the log queryable. |

## Index

**GENERATED — do not edit below.** Rebuild with `bash docs/decisions/build_index.sh`.

| # | Decision | Date | Status | Touches |
|---|---|---|---|---|
HEAD

    for f in [0-9][0-9][0-9][0-9]-*.md; do
        num="${f%%-*}"
        title=$(sed -n 's/^# //p' "$f" | head -1)
        date=$(sed -n 's/^date: //p' "$f" | head -1)
        status=$(sed -n 's/^status: //p' "$f" | head -1)
        touches=$(awk '/^touches:/{f=1;next} f&&/^  - /{sub(/^  - /,"");printf "%s%s", sep, $0; sep="<br>"; next} f&&!/^  - /{exit}' "$f")
        echo "| $num | [$title]($f) | $date | $status | \`${touches//<br>/\`<br>\`}\` |"
    done

    cat <<'FOOT'

## Human check

Before changing anything under `gars/`, grep this index for the path you are about to touch. If a
decision names it, read that decision first.
FOOT
} > CONTEXT.md

echo "wrote $(pwd)/CONTEXT.md"
