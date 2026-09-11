# The checkout smokes — what the agent under test is given, read from its own record

Each folder is one headless session driven by `smoke_run_tree.py`.
It sends one neutral line ("Reply with the single word: ready.") to `claude-haiku-4-5-20251001`, in a checkout built by `drive.clean_run_tree()` from commit `ee37426`.

None of them is a walk or a take.
No task line was sent, no fixture was built, and nothing here is graded or used to fix a script.
They exist because review 11 found that the checkout's guards had been verified against constructed strings; these read what a real session was actually given.

| Smoke | Isolation in force | What `check_take.inherited_context()` read from the transcript |
|---|---|---|
| 1 | none | two working directories granted by the operator's user settings, and 49 account-connector tools |
| 2 | `--setting-sources project,local --strict-mcp-config` | nothing |
| 3 | the same flags, and `ENABLE_CLAUDEAI_MCP_SERVERS=false` in the session's environment | nothing |
| 4 | the same as smoke 3 | nothing |

Smoke 3's `report.json` lists the flags and not the environment variable, because the field that records it was added after that run.
Smoke 4 was run on the recorder as committed, and its report records both.

In all four, the checkout had one commit, the subject `checkout`, no remote, a clean status and the git user `gars`, and no leak word was found in the loaded context.

Each `transcript.jsonl` is the session file with one field removed: `session_context.userEmail`, the signed-in account's email address, which Claude Code injects into every session.
`scrub.json` beside each records the sha256 before and after.
`scrub.py` asserts that every record a grader reads is identical before and after, and that the address appears nowhere in what it wrote.

The `sweep_hits` in each report are the lines of the checkout that still mention the evaluations.
`prereg-draft.json` names them under `run_location.residual`.
