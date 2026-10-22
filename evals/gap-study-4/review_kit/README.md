# The review kit: operator notes

These notes are for the operator who runs a pre-freeze review round.
The reviewer is never handed them: `build_kit.py` gives it `BRIEF.md`, `why.md`, the bytes, `athena/`, `COMMIT` and a clone.

## A round, in order

1. On the remote runner, in a throwaway child of the head under review, run `python3 evals/gap-study-4/review_kit/athena_outputs.py <outputs folder> [--holdout-tool <aegis holdout.py>]`. It runs `run_checks.py`, each command of `freeze_rehearsal.py`'s `COMMANDS` directly, `freeze.py --check` and the three legs, and writes one file per gate with its own `command:`, `commit:` and `exit:` lines and the masked tail of its output. Copy the folder back to the machine that builds the kit.
2. Build the folder outside the Brain and this repository: `python3 evals/gap-study-4/review_kit/build_kit.py <folder> --n <N> --athena <outputs folder> [--previous <bytes>]`. It refuses an outputs folder that is empty or nested, or that holds a link, a dotfile, an empty file, a file without the line `commit: <the head sha>`, or a file carrying an absolute path, a person's name or an operator marker, and copies the rest to `<folder>/athena/`. Never fill `athena/` by hand: that skips every one of these refusals.
3. Register the row and commit it alone: `python3 evals/gap-study-4/review_kit/rounds.py --add --kind prefreeze --folder <folder>`. The row hashes the whole folder, `athena/` included.
4. Read the row's session id (`rounds.py --session-id <row>`) and launch: `python3 evals/gap-study-4/review_kit/launch.py <folder> <id>`. A session cut off after its first agent turn is resumed with `--resume`, never relaunched.
5. Run `python3 evals/gap-study-4/review_kit/blindness.py <folder>` on the reviewer's own session file.
6. Commit the report exactly once: `python3 evals/gap-study-4/review_kit/commit_review.py <folder> <N>`.

## Before round 1: the skills smoke

The reviewer is launched with the driver's isolation flags (`--setting-sources project,local`, `--strict-mcp-config`), `--effort medium`, auto memory off, and an environment built from `launch.py`'s `ALLOWED_ENV` alone.
Whether skills kept in the operator's home folder (directly, one level deeper under the account-synced folder, or as plugins) still reach a session launched that way on today's client has not been measured.
One such skill carries the operator's coordinating-session name (`lane-orchestrator`), and the Brain keeps its own skills too.
So before round 1 opens, one turn is launched exactly as a reviewer is, and its loaded skills are listed.

The client's built-in skills, the only names the smoke admits:

BUILT-IN SKILLS: dataviz, update-config, keybindings-help, code-review, simplify, fewer-permission-prompts, loop, schedule, claude-api, workflow-authoring, run, init, security-review

How the list was obtained: from the `skill_listing` records of round 3's pre-freeze reviewer sessions, headless sessions launched outside the Brain with the same isolation flags (the sessions named by `evals/gap-study-3/review_kit/prefreeze-3-blindness.txt`, `prefreeze-4-blindness.txt` and `prefreeze-5-blindness.txt`). Each recorded `skillCount` 13 and exactly these 13 names. Read from those session files on Wed 21 Oct 2026 by lane review-kit-port; no session was launched to obtain it.

1. Make a throwaway folder outside the Brain and this repository, holding a `BRIEF.md` with the one line `Reply with the single word done, and stop.`, an empty `study/` made by `git init` (no remote), a `COMMIT` file and an `athena/` folder with one placeholder file, so `launch.py`'s folder checks pass. It holds no study bytes.
2. Launch it with no session id: `python3 evals/gap-study-4/review_kit/launch.py <smoke folder>`. The id is a fresh uuid4 and belongs to no row: the smoke binds no bytes and is not a round. Never launch it under a row's derived id.
3. Run `python3 evals/gap-study-4/review_kit/blindness.py <smoke folder>`.
4. List the skills the session was offered, from the session file `blindness.py` read (`~/.claude/projects/*/<id>.jsonl`, the id in `<smoke folder>-launch/SESSION`):

   ```
   python3 -c 'import json,sys
   for l in open(sys.argv[1]):
       r = json.loads(l); a = r.get("attachment") or {}
       if r.get("type") == "attachment" and "skill" in str(a.get("type", "")): print(a.get("type"), a.get("skillCount"), a.get("names"))' <session file>
   ```

5. Read the effort the session ran at: every record of the session file that carries a top-level `effort` field.
6. Read `<smoke folder>-launch/env-names.txt`, the names (never the values) `launch.py` passed.

What the smoke must show, every item, before round 1 opens:

- `<smoke folder>-launch/launch.log` records exit 0, and the session ran one turn.
- The session's own record names the model `claude-opus-5-5`.
- At least one record carries a top-level `effort` field, and every such field reads `medium`.
- `env-names.txt` lists only names `ALLOWED_ENV` holds plus `ENABLE_CLAUDEAI_MCP_SERVERS` and `CLAUDE_CODE_DISABLE_AUTO_MEMORY`.
- `blindness.py` prints UNEXPLAINED 0 on every marker row, `lane-orchestrator` included, and 0 absolute paths outside the folder.
- Every skill name the listing records is on the built-in list above, and only names on that list pass: a name from the operator's home folder, the account-synced folder, a plugin or the Brain fails the smoke, and so does a new built-in name, until it is reviewed and added to the list on its own commit.
- The skill listing was read: if step 4 prints no skill record at all, the smoke has not measured the list and does not pass. Record that, and find the record the client uses before trusting a silence.

If any item fails, round 1 does not open.
The kit is changed (a reviewed change on its own commit; if the client cannot run without a further environment name, that name joins `ALLOWED_ENV` with its reason), and the smoke runs again.
Keep the smoke folder, its launch folder and the `blindness.py` output beside the review folders, and name them in the round 1 hand-back; they are never committed into the study tree.
