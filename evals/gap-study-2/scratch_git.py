#!/usr/bin/env python3
"""The one road to a throwaway git repository in this harness: `git init`, with background maintenance off.

    from scratch_git import init
    init(path)

Found in CI on 16 September 2026, on `dc091af` and its re-run: the mutation battery raised `OSError: [Errno 39]
Directory not empty` while deleting a sandbox's `.git` (attempt 1) and `.git/objects` (attempt 2), after two
different mutations. Git 2.55, the runner's, runs `git maintenance run --auto` after `commit`, detached, with the
geometric strategy for unscheduled maintenance; its repack task starts once the approximate loose-object count
(the `objects/17` bucket times 256) is over 256. Every git sandbox is over it: measured on 20 sandboxes each,
363 loose objects and 2 in that bucket at `c423366`, 395 and 3 at `dfdf82e`. So a background repack writes into
`.git/objects` while `TemporaryDirectory.cleanup` removes it. The race predates the walks; `c423366`'s green
battery won it, and the walks' extra objects made the repack slower and the race easier to lose. This Mac's git
2.36 has no geometric auto-repack, which is why the battery was green here.

`maintenance.auto false` in the repository's own config stops every git process in it from starting that
maintenance: the harness's own commits, and the commits a guard makes inside a sandbox.

NOT USED for a take's run tree (`drive.clean_run_tree`): that repository is part of the agent's environment, and
a setting an agent can read there is a condition of the experiment, not the harness's to change. The takes run on
the operator's machine, whose git has no geometric auto-repack; the run tree holds about 219 loose objects.

No model, no network. stdlib only.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# The setting and its value, named once so the guard reads what this module writes.
MAINTENANCE_KEY = "maintenance.auto"
MAINTENANCE_VALUE = "false"


def init(path: Path | str) -> None:
    """Create a git repository at `path` whose own config starts no background maintenance."""
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", MAINTENANCE_KEY, MAINTENANCE_VALUE],
                   check=True, capture_output=True)
