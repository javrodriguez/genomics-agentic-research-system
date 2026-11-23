VERDICT: CHANGES

# Review: lane blindness-sidechains at 5a6dc215

Fresh independent reviewer, Sat 24 Oct 2026 16:34 EDT.
Candidate: `lane/blindness-sidechains` 5a6dc215504f6c6b2baaa2019547878bbe178be4, base `freeze/r4-20261021` 96c1d959.
All Mac work behind `mac_slot.py light-ok --tests --work gap-study-r4` (light ok, load1 3.02), python3.12.
No code changed; the round folder, its `-launch` folder and the session files were only read (blindness.py's `main()` was not called, because it writes `round1-launch/blindness.txt`; `report()` was called from a scratch script instead).

## What holds (verified)

- K15.sidechains red at base: head's test file over base's blindness.py gives `Ran 8 tests ... FAILED (errors=8)`, every one `AttributeError: ... has no attribute 'analyse'`.
- Green at head, in the clone: `test_review_kit.py` 39 OK; `--witnesses` 61/61 red, the 22 K15.sidechains witnesses each RED.
  (In a `git archive` copy one Markers test errors and one witness reads FAIL only because the copy is not a git repository; not a candidate defect.)
- Round 1 re-run, read-only, `report(folder, sid)` on d13b95c5: byte-identical to the builder's `round1-rerun.txt` except one trailing newline (`print` versus my `end=""`).
  6 sub-agent files, 0 missing, 0 unlaunched; section 4: 37 hits, 36 traced, 1 UNEXPLAINED (round 2's name); sections 1 and 3: 0 UNEXPLAINED.
- Round 1's 36 traced hits stay traced when findings 1 and 2 are fixed by hand (tails restricted to ones carrying the marker, corpus restricted to files older than `folder-at-launch.txt`): 36 of 37 in every variant. So round 1's reading does not depend on the holes below.
- Adversarial fixtures that held: an operator marker in a hand-back, and the Brain path row, are never explained; a symlinked file or directory in the folder is excluded and the hit stays UNEXPLAINED; a hand-back only in `prompt` (no `rendered`) is read once; a launched agent with no session file is listed as missing and its hit is UNEXPLAINED; the Write tool's own file inside the folder is excluded (control for finding 2).
- rounds.json claim: only `COPIED.d/blindness-sidechains.json` claims `review_kit/rounds.json` on every ref of this clone and of the canonical aegis repo; `copy_manifest.py --check` at head: `ok: 727 files from 73 fragment(s)`; copy_manifest refuses a second claim itself ("a file has one owner"); 411ecaf8's fragment did not yet claim it. No double claim.

Probe script: `/private/tmp/claude-501/-Users-javrodher-glitch/5da39513-9adc-4587-8d29-3722641cf776/scratchpad/rev-bs/probes.py` (P1 to P11, each its own temp tree).

## Findings

1. MAJOR. A path tail that drops the marker explains the marker.
   `candidates()` returns every tail with a `/`, including tails that no longer hold the marker word.
   P1: hand-back `see evals/gap-study-3/tests/test_x.py`, folder holds `study/evals/gap-study-4/tests/test_x.py`, sub-agent read it; result `round 3's folder name: (total 1, traced 1, UN 0)`.
   Round 3's folder name is explained by a round 4 file.
   Fix: keep only candidates that still contain the marker word (round 1 is unaffected: 36 of 37 either way), and a witness for it.

2. MAJOR. "A file that no session wrote" covers only the Write/Edit tools.
   `note_writes` records in-folder writes only for WRITE_TOOLS; a shell write inside the folder (`cat >`, `cp`, `tee`, a Python run that drops files) stays in the corpus, and the shell command is in the sub-agent's own traffic, so the leak explains itself.
   P2: sub-agent `cat > <folder>/study/scratch.md <<EOF ... gars-eval-v3 ... EOF`, hand-back quotes it: `(1, 1, 0)`; the same with the Write tool (P2b): `(1, 0, 1)`.
   On the real round 1, 68 files written after `folder-at-launch.txt` (all `__pycache__/*.pyc`) are in the 11,834-file corpus.
   `folder-at-launch.txt` lists top-level names only, so anything later created under `study/` counts as "in the folder at launch".
   Fix: build the corpus from a launch-time manifest (the rounds.json row already hashes the whole folder; a per-file list with hashes beside `folder-at-launch.txt` would bind it) or, at minimum, drop files whose mtime is after the launch stamp.

3. MAJOR. A sub-agent's report read through another tool is counted zero times.
   Only Agent/Task tool results, `<agent-message>` texts and `<task-notification>` texts are hand-backs; tool results are never scanned otherwise.
   P9: reviewer calls `TaskOutput` for agent aaa and gets `report: gars-eval-v3 floor, per the lane-orchestrator` -> no hand-back, sections 1/3/4 all empty, an operator marker included.
   The same holds for a Read of the notification's `<output-file>` (`.../tasks/<aid>.output`), which section 5 lists only as a masked outside path that does not bind.
   The threat model says never zero. Fix: treat any reviewer tool result whose input names a launched agent id or a `tasks/<aid>.output` path as a hand-back from that agent.

4. MINOR. An Agent result with no recoverable id is dropped silently.
   If neither `toolUseResult.agentId` nor `agentId: ` is in the body, no hand-back is recorded and section 2 says nothing.
   P8: foreground Agent result `Done: gars-eval-v3 ...; the lane-orchestrator said so.` with no id -> 0 hand-backs, 0 hits.
   Fix: attribute it to an unknown agent (never traced) and list Agent calls without an id in section 2.

5. MINOR. "Read it there" includes what the sub-agent typed.
   `traffic` is tool inputs plus tool results, so a word in its own command or Write content counts as read.
   Round 1 shows the shape: the one UNEXPLAINED extent `round 2/3` is in agent aa07ac8b's traffic only through one of its own tool inputs.
   Fix: trace against tool results only.

6. MINOR. A relayed nested hand-back can never trace (fail-closed false positive).
   P7: child nnn reads the folder and hands back to aaa (traced); aaa relays it to the reviewer -> UNEXPLAINED, because the child's hand-back is not in aaa's traffic.
   No round 1 agent nested, so no effect yet; a round with nested agents that relay cannot read 0.
   Fix: let a parent's hit trace through the child hand-backs it received, with the child's own trace required.

7. NIT. Double counts on shapes not in the real data.
   The same sidechain records inline (isSidechain) and in `subagents/agent-<id>.jsonl` are concatenated, not de-duplicated by uuid (P10: one `north star` reads 2).
   A queued_command whose `rendered` reflows the prompt is read twice (P5b: 2 hits for 1); round 1's 6 queued commands all carry the prompt verbatim, so the rule holds there.

8. NIT. Non-operator rows trace by word, so coincident study words pass by design.
   P3: hand-back "Javier's notes say round 3 failed on the scanner", a study file holds "round 3's successor" -> traced.
   That is the ruling's own limit (only operator rows are refused outright); worth one line in the docstring so the reader of section 4 knows it.

9. NIT. Section 4's "12 hand-backs from 6 agents" on round 1 counts the 6 task notifications, which say the report is not repeated and carry no hit; and red-at-base is by AttributeError, not by an assertion on K15.sidechains.

10. INFO (not a defect). Round 1's remaining UNEXPLAINED hit is the extent `round 2/3` in agent aa07ac8b's hand-back; `round 2` is in the folder and in its traffic, `round 2/3` is not in the folder. The rule as ruled reads it UNEXPLAINED; whether that voids round 1 is the orchestrator's call.

## Stop rule

Findings 1 to 3 are on the threat model (a leak read as explained; a hit counted zero times), so this is CHANGES, not a nit stop.
After 1 to 3 (each with a witness), 4 to 6 are cheap and should ride the same commit; 7 to 9 are nits.
