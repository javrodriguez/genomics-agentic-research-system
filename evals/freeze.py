#!/usr/bin/env python3
"""Which commit froze the pre-registration -- and whether this checkout can prove it.

WHY THIS IS ITS OWN MODULE. run.py records the freeze commit in every results file and
check_results.py re-reads the frozen bytes from it. Two copies of "which commit froze this" would
drift, and the drift would be invisible: both would keep printing a sha. One answer, one place,
for the same reason evals/transcript.py is the one parser and evals/stated_count.py is the one
count reader.

THE DEFECT THIS EXISTS TO CLOSE, because it was live and it was silent. Both callers derived the
sha with `git log --reverse -- evals/prereg.json` and took the first line. In a SHALLOW clone --
which is what `actions/checkout` makes by default, at depth 1 -- that command does not return
nothing. It returns the grafted head, because the head is the only commit there and a grafted
root looks like it added every file in the tree. So the checker named the wrong commit, read
`git show <head>:evals/prereg.json`, compared it to the working copy it came from, found them
identical and printed:

    ok            prereg.json byte-identical to f93fdd56

That is a green that means nothing. It verified the file against itself and would have gone on
doing so in CI forever, while the ordering claim it exists to prove -- that the thresholds were
fixed BEFORE the runs -- was never checked at all. Reproduced with `git clone --depth 1` before
this module was written; the `--diff-filter=A` probe that looks like the obvious fix does NOT
catch it, for the same grafted-root reason.

SO THE ANSWER CARRIES ITS OWN WARRANT. `freeze_ref()` returns whether the checkout can prove the
ordering, and when it cannot it says why and names the fix. A caller that needs the proof must
refuse rather than pass: an unverifiable freeze is not a satisfied one.

No model is called. stdlib only.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
PREREG_PATH = "evals/prereg.json"


def _git(*args: str) -> tuple[int, str]:
    try:
        out = subprocess.run(["git", "-C", str(REPO), *args],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return out.returncode, out.stdout.strip()


def is_shallow() -> bool:
    code, out = _git("rev-parse", "--is-shallow-repository")
    return code == 0 and out.strip() == "true"


def freeze_ref() -> dict:
    """{'sha', 'verifiable', 'why'} -- the freeze commit, and whether it can be trusted here.

    `verifiable` False means this checkout cannot prove the ordering. It is never a soft warning:
    the whole claim of a pre-registered evaluation is that the thresholds were pushed before the
    first run, and a checkout without the history to show it has not weakened the claim, it has
    simply not checked it.
    """
    code, _ = _git("rev-parse", "--git-dir")
    if code != 0:
        return {"sha": None, "verifiable": False,
                "why": "git is not available here, or this is not a repository, so the commit "
                       "that froze the pre-registration cannot be identified"}

    if is_shallow():
        return {"sha": None, "verifiable": False,
                "why": "this is a SHALLOW clone, so the history that proves the ordering was "
                       "never fetched. Do not read the sha git offers here: a grafted root "
                       "appears to have added every file in the tree, so the head would be named "
                       "as the freeze commit and would then compare byte-identical to itself. "
                       "Fix: clone with full history, or set `fetch-depth: 0` on actions/checkout."}

    code, out = _git("log", "--format=%H", "--reverse", "--", PREREG_PATH)
    shas = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if code != 0 or not shas:
        return {"sha": None, "verifiable": False,
                "why": f"git records no commit touching {PREREG_PATH}; either it has never been "
                       f"committed, or this checkout has no history for it"}

    return {"sha": shas[0], "verifiable": True,
            "why": f"the first commit touching {PREREG_PATH} in a checkout with full history"}


def frozen_bytes(sha: str) -> bytes | None:
    """The pre-registration exactly as that commit recorded it, or None."""
    try:
        out = subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:{PREREG_PATH}"],
                             capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


if __name__ == "__main__":
    import json
    print(json.dumps(freeze_ref(), indent=2))
