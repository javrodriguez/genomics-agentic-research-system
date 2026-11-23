"""The sidecar's fixed launch contract: constants only, no imports, no code.

Preflight imports it plainly (`from box import sidecar_contract`) so the box audit can bind every name it reads
(glitch-06 ruling 1, 14 Oct 2026; the run_take audit W4B3-3/W4B4-1). sidecar.py runs alone in its image and its own
audit admits no import of another file, so it carries the same literal values; tests/test_live_box.py binds the two.
"""

from __future__ import annotations

# The program's path in the sidecar image and the interpreter that runs it, alone, on the image's Python.
PROGRAM = "/opt/w/sidecar.py"
INTERPRETER = ("python3", "-I", "-B")
# The watcher's own user after the privilege drop; the one capability it keeps.
WATCHER_USER = "10002:10002"
ADDED_CAPABILITY = "DAC_READ_SEARCH"
# Boot-only capabilities: setpriv execs the watcher as PID 1 after discarding every other privilege.
# Measured on Athena's pinned image; see live-box-evidence-2026-10-13/sidecar-setpriv-probe.json.
BOOT_USER = "0:0"
BOOT_CAPABILITIES = (ADDED_CAPABILITY, "SETUID", "SETGID", "SETPCAP")
# Docker 29.8.1 inspect spelling/order, measured in sidecar-launch-inspect.json.
BOOT_INSPECT_CAPABILITIES = ("CAP_DAC_READ_SEARCH", "CAP_SETGID", "CAP_SETPCAP", "CAP_SETUID")
WATCHER_LAUNCHER = ("/usr/bin/setpriv", "--reuid=10002", "--regid=10002", "--clear-groups",
                    "--inh-caps=-all,+dac_read_search", "--ambient-caps=-all,+dac_read_search",
                    "--bounding-set=-all,+dac_read_search", "--no-new-privs", "--")
