# The review kit: operator notes

These notes are for the operator who runs a pre-freeze review round.
The reviewer never reads them: `build_kit.py` hands it `BRIEF.md`, `why.md`, the bytes and a clone, nothing else.

## A round, in order

1. Have the remote runner run the heavy gates at the commit under review, one file per command, each naming the command, the full commit sha and the tail of its output: `run_checks.py`, each command of `freeze_rehearsal.py`'s `COMMANDS` run directly, and `freeze.py --check`.
2. Build the folder outside the Brain and this repository: `python3 evals/gap-study-4/review_kit/build_kit.py <folder> --n <N> --athena <outputs folder> [--previous <bytes>]`. It refuses an outputs folder that is empty, nested, holds a link or an empty file, or holds a file that does not name the commit the clone is at, and copies the rest to `<folder>/athena/`.
3. Register the row and commit it alone: `python3 evals/gap-study-4/review_kit/rounds.py --add --kind prefreeze --folder <folder>`. The row hashes the whole folder, `athena/` included.
4. Read the row's session id (`rounds.py --session-id <row>`) and launch: `python3 evals/gap-study-4/review_kit/launch.py <folder> <id>`. A session cut off after its first agent turn is resumed with `--resume`, never relaunched.
5. Run `python3 evals/gap-study-4/review_kit/blindness.py <folder>` on the reviewer's own session file.
6. Commit the report exactly once: `python3 evals/gap-study-4/review_kit/commit_review.py <folder> <N>`.

## Before round 1: the skills smoke

The reviewer is launched with the driver's isolation flags (`--setting-sources project,local`, `--strict-mcp-config`) and with auto memory off.
Whether skills kept in the operator's home folder still reach a session launched that way has not been measured.
One such skill carries the operator's coordinating-session name (`lane-orchestrator`), and the Brain keeps its own skills too.
So before round 1 opens, one turn is launched exactly as a reviewer is, and its loaded skills are listed.

1. Make a throwaway folder outside the Brain and this repository, holding a `BRIEF.md` with the one line `Reply with the single word done, and stop.` and an empty `study/` made by `git init` (no remote), so `launch.py`'s folder checks pass. It holds no study bytes.
2. Launch it with no session id: `python3 evals/gap-study-4/review_kit/launch.py <smoke folder>`. The id is a fresh uuid4 and belongs to no row: the smoke binds no bytes and is not a round. Never launch it under a row's derived id.
3. Run `python3 evals/gap-study-4/review_kit/blindness.py <smoke folder>`.
4. List the skills the session was offered, from the session file `blindness.py` read (`~/.claude/projects/*/<id>.jsonl`, the id in `<smoke folder>-launch/SESSION`):

   ```
   python3 -c 'import json,sys
   for l in open(sys.argv[1]):
       r = json.loads(l); a = r.get("attachment") or {}
       if r.get("type") == "attachment" and "skill" in str(a.get("type", "")): print(json.dumps(a)[:4000])' <session file>
   ```

   and compare the names with `ls ~/.claude/skills` and the Brain's own `.claude/skills/`.

What the smoke must show, every item, before round 1 opens:

- `<smoke folder>-launch/launch.log` records exit 0, and the session ran one turn.
- The session's own record names the model `claude-opus-5-5`.
- `blindness.py` prints UNEXPLAINED 0 on every marker row, `lane-orchestrator` included, and 0 absolute paths outside the folder.
- The skill listing names no skill from the operator's home folder and none from the Brain: no name beginning `lane-orchestrator`, and no name that `ls ~/.claude/skills` or the Brain's `.claude/skills/` prints.
- The skill listing was read: if step 4 prints no skill record at all, the smoke has not measured the list and does not pass. Record that, and find the record the client uses before trusting a silence.

If any item fails, round 1 does not open.
The isolation is changed in the kit (a reviewed change on its own commit), and the smoke runs again.
Keep the smoke folder, its launch folder and the `blindness.py` output beside the review folders, and name them in the round 1 hand-back; they are never committed into the study tree.
