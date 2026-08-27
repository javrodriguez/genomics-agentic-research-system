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
| Frontmatter | `date`, `status` (`standing` / `superseded`), `kind` (`decision` / `lesson` / `defect`), `touches` (paths this decision constrains), `symptoms` (optional; the observable failure) |
| Superseding | Never edit a decision to reverse it. Write a new one and set the old to `status: superseded`, naming its replacement. |
| `touches` | The files a reader must not change without reading this first. Keep it accurate — it is what makes the log queryable by path. |
| `symptoms` | The failure as someone would grep for it ("login-node SIGKILL", "anonymous gene table") — what makes the log queryable by symptom, so a recurrence finds its precedent. One line per distinct observable failure; omit for pure design decisions. |

## Index

**GENERATED — do not edit below.** Rebuild with `bash docs/decisions/build_index.sh`.

| # | Decision | Date | Status | Kind | Touches | Symptoms |
|---|---|---|---|---|---|---|
HEAD

    for f in [0-9][0-9][0-9][0-9]-*.md; do
        num="${f%%-*}"
        title=$(sed -n 's/^# //p' "$f" | head -1)
        date=$(sed -n 's/^date: //p' "$f" | head -1)
        status=$(sed -n 's/^status: //p' "$f" | head -1)
        kind=$(sed -n 's/^kind: //p' "$f" | head -1)
        touches=$(awk '/^touches:/{f=1;next} f&&/^  - /{sub(/^  - /,"");printf "%s%s", sep, $0; sep="<br>"; next} f&&!/^  - /{exit}' "$f")
        symptoms=$(awk '/^symptoms:/{f=1;next} f&&/^  - /{sub(/^  - ["'"'"']?/,"");sub(/["'"'"']$/,"");printf "%s%s", sep, $0; sep=" · "; next} f&&!/^  - /{exit}' "$f")
        echo "| $num | [$title]($f) | $date | $status | ${kind:--} | \`${touches//<br>/\`<br>\`}\` | ${symptoms:--} |"
    done

    cat <<'FOOT'

## Human check

Before changing anything under `gars/`, grep this index for the path you are about to touch. If a
decision names it, read that decision first. Debugging a failure? Grep the Symptoms column for
what you are seeing — a recurrence usually has a precedent here.
FOOT
} > CONTEXT.md

echo "wrote $(pwd)/CONTEXT.md"
