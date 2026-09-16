#!/usr/bin/env python3
"""A throwaway repository this harness builds starts no background git maintenance.

    python3 evals/gap-study-2/test_harness.py TheScratchRepositoriesStartNoBackgroundMaintenance

Found in CI on 16 September 2026 (see scratch_git.py): git 2.55 runs a detached repack after `commit` in every
sandbox of the mutation battery, and the battery crashed deleting a `.git` the repack was still writing. So
every repository the harness creates goes through scratch_git.init, which sets `maintenance.auto false` in the
repository's own config. These tests read that setting from the built repositories, and scan the study's
sources for a `git init` that goes around the one road.

The one exception is drive.py's run tree, the take's own checkout, which is part of the agent's environment.
The scan names every file whose text may carry the raw form (that one, the road itself, and the mutation module
that plants it), so a further exception cannot arrive silently.

No model, no network. stdlib only.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import scratch_git  # noqa: E402

# A `git init` spelled out in a source file, in any of the forms this harness has used.
RAW_INIT = re.compile(r'''["']init["']\s*,\s*["']-q["']''')
# The folders under the study that hold harness code, besides its top level.
SOURCE_FOLDERS = ("graders", "fixtures", "controls")
# The files whose text may carry a raw `git init`, and why. Only drive.py creates a repository that way.
PERMITTED = {"scratch_git.py": "the one road itself",
             "drive.py": "the take's run tree is the agent's environment, not the harness's to configure",
             "mutations_scratch_git.py": "it plants the raw form, in a throwaway copy, for this scan to refuse"}


def source_files() -> list[Path]:
    """The harness's own Python: the study folder's top level and its code folders, never a live record folder
    (walks, transcripts, results and the rest), which this suite may not read."""
    files = list(HERE.glob("*.py"))
    for folder in SOURCE_FOLDERS:
        files.extend(p for p in (HERE / folder).rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(files)


def maintenance_setting(repo: Path) -> str:
    r = subprocess.run(["git", "-C", str(repo), "config", "--local", "--get", scratch_git.MAINTENANCE_KEY],
                       capture_output=True, text=True)
    return r.stdout.strip()


def load_mutations():
    """This study's mutations.py, imported by name, as tests_battery_report.py does."""
    import mutations
    if Path(mutations.__file__).resolve() != HERE / "mutations.py":
        raise ImportError(f"imported another study's mutations.py: {Path(mutations.__file__).name} from outside this study")
    return mutations


class TheScratchRepositoriesStartNoBackgroundMaintenance(unittest.TestCase):

    def test_init_writes_the_setting_into_the_repository_it_creates(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "r"
            scratch_git.init(repo)
            self.assertTrue((repo / ".git").is_dir(), "scratch_git.init created no repository")
            self.assertEqual(maintenance_setting(repo), "false",
                             "a scratch repository would start background maintenance after a commit")

    def test_the_battery_sandbox_creates_its_repository_through_the_one_road(self):
        """Read from Sandbox's source, not by building one: a sandbox copies the whole study, walks and COSTS.md
        included, and this suite reads no live state (TheSuiteNeverReadsLiveState). The battery builds real
        sandboxes on every run, and the scan below refuses a raw init in mutations.py."""
        import inspect
        source = inspect.getsource(load_mutations().Sandbox.__init__)
        self.assertIn("scratch_git.init(self.root)", source,
                      "the battery sandbox does not go through scratch_git.init, so it can start background maintenance")

    def test_no_source_creates_a_repository_around_the_one_road(self):
        offenders = []
        for path in source_files():
            if path.name in PERMITTED:
                continue
            for n, line in enumerate(path.read_text().splitlines(), 1):
                if RAW_INIT.search(line) and "RAW_INIT" not in line:
                    offenders.append(f"{path.relative_to(HERE)}:{n}")
        self.assertEqual(offenders, [], "a git init that does not go through scratch_git.init, so its repository "
                                        "can start background maintenance: " + ", ".join(offenders))

    def test_the_permitted_list_names_only_files_that_exist(self):
        for name in PERMITTED:
            self.assertTrue((HERE / name).is_file(), f"PERMITTED names {name}, which is not in this study")


if __name__ == "__main__":
    unittest.main()
