#!/usr/bin/env bash
# SessionStart hook (decision 0033): rebuild the generated index, then print the per-project
# catch-up so a session boots knowing where every project stands. The only write is
# projects/_index.md — a generated file whose authority is elsewhere. Pin failures refuse session initialization (R-099).
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$WS/_system/tools/pins.py" || exit 2
bash "$WS/_system/build_projects_index.sh" "$WS" >/dev/null 2>&1 || true
python3 "$WS/_system/project_state.py" 2>/dev/null || true
